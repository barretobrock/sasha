#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import requests
import pandas as pd
from typing import List, Optional, Tuple, Union
from datetime import datetime as dt
from random import randint
from slacktools import SlackBotBase, GSheetReader, BlockKitBuilder
from .linguistics import Linguistics
from ._version import get_versions


class Sasha:
    """Handles messaging to and from Slack API"""

    def __init__(self, log_name: str, xoxb_token: str, xoxp_token: str, ss_key: str, onboarding_key: str,
                 debug: bool = False):
        """
        Args:
            log_name: str, name of the kavalkilu.Log object to retrieve
            xoxb_token: str, bot token to use
            xoxp_token: str, user token to use
            ss_key: str, spreadsheet containing various things Sasha reads in
            onboarding_key: str, link to onboarding documentation
            debug: bool, if True, will use a different set of triggers for testing purposes
        """
        self.debug = debug
        self.bot_name = f'Sasha {"Debugnova" if debug else "Produdnika"}'
        self.triggers = ['sasha', 's!']
        self.main_channel = ''  # test
        self.emoji_channel = ''  # emoji_suggestions
        self.general_channel = ''  # general
        self.alerts_channel = ''  # #alerts
        self.approved_users = ['', '']    #b, m
        self.bkb = BlockKitBuilder()
        self.ling = Linguistics()
        # Bot version stuff
        version_dict = get_versions()
        self.version = version_dict['version']
        self.update_date = pd.to_datetime(version_dict['date']).strftime('%F %T')
        self.bootup_msg = [self.bkb.make_context_section([
            f"*{self.bot_name}* *`{self.version}`* booted up at `{dt.now():%F %T}`!",
            f"(updated {self.update_date})"
        ])]

        # Intro / help / command description area
        intro = f"I'm *{self.bot_name}* (:regional_indicator_s: for short).\n" \
                f"I can help do stuff for you, but you'll need to call my attention first with " \
                f"*`{'`* or *`'.join(self.triggers)}`*\n Example: *`{self.triggers[0]} hello`*\n" \
                f"Here's what I can do:"
        avi_url = "https://avatars.slack-edge.com/2020-07-10/1219810342855_04c9966e835417fadde7_512.png"
        avi_alt = 'avatar'
        cat_basic = 'basic'
        cat_useful = 'useful'
        cat_notsouseful = 'not so useful'
        cat_lang = 'language'
        cmd_categories = [cat_basic, cat_useful, cat_notsouseful, cat_lang]

        commands = {
            r'^help': {
                'pattern': 'help',
                'cat': cat_basic,
                'desc': 'Description of all the commands I respond to!',
                'value': '',
            },
            r'^about$': {
                'pattern': 'about',
                'cat': cat_useful,
                'desc': 'Bootup time of Sasha\'s current instance, his version and last update date',
                'value': self.bootup_msg,
            },
            r'good bo[tiy]': {
                'pattern': 'good bo[tiy]',
                'cat': cat_basic,
                'desc': 'Did I do something right for once?',
                'value': 'thanks <@{user}>!',
            },
            r'^time$': {
                'pattern': 'time',
                'cat': cat_basic,
                'desc': 'Display current server time',
                'value': [self.get_time],
            },
            r'^speak$': {
                'pattern': 'speak',
                'cat': cat_basic,
                'desc': '_Really_ basic response here.',
                'value': 'woof',
            },
            r'.*inspir.*': {
                'pattern': '<any text with "inspir" in it>',
                'cat': cat_notsouseful,
                'desc': 'Uploads an inspirational picture',
                'value': [self.inspirational, 'channel'],
            },
            r'.*tihi.*': {
                'pattern': '<any text with "tihi" in it>',
                'cat': cat_notsouseful,
                'desc': 'Giggles',
                'value': [self.giggle],
            },
            r'^e[nt]\s': {
                'pattern': '(et|en) <word-to-translate>',
                'cat': cat_lang,
                'desc': 'Offers a translation of an Estonian word into English or vice-versa',
                'value': [self.ling.prep_message_for_translation, 'message', 'match_pattern']
            },
            r'^ekss\s': {
                'pattern': 'ekss <word-to-lookup>',
                'cat': cat_lang,
                'desc': 'Offers example usage of the given Estonian word',
                'value': [self.ling.prep_message_for_examples, 'message', 'match_pattern']
            },
            r'^lemma\s': {
                'pattern': 'lemma <word-to-lookup>',
                'cat': cat_lang,
                'desc': 'Determines the lemma of the Estonian word',
                'value': [self.ling.prep_message_for_root, 'message', 'match_pattern']
            },
            r'^wfh\s?(time|epoch)': {
                'pattern': 'wfh (time|epoch)',
                'cat': cat_useful,
                'desc': 'Prints the current WFH epoch time',
                'value': [self.wfh_epoch]
            },
            r'^ety\s': {
                'pattern': 'ety <word>',
                'cat': cat_useful,
                'desc': 'Gets the etymology of a given word',
                'value': [self.ling.get_etymology, 'message', 'match_pattern']
            }
        }
        # Initiate the bot, which comes with common tools for interacting with Slack's API
        self.st = SlackBotBase(log_name, triggers=self.triggers, team='orbitalkettlerelay',
                               main_channel=self.main_channel, xoxp_token=xoxp_token, xoxb_token=xoxb_token,
                               commands=commands, cmd_categories=cmd_categories)
        self.bot_id = self.st.bot_id
        self.user_id = self.st.user_id
        self.bot = self.st.bot

        self.st.message_main_channel(blocks=self.bootup_msg)

        # Lastly, build the help text based on the commands above and insert back into the commands dict
        commands[r'^help']['value'] = self.st.build_help_block(intro, avi_url, avi_alt)
        # Update the command dict in SlackBotBase
        self.st.update_commands(commands)

        # These data structures will help to better time the dissemination of notifications
        #   (e.g., instead of notifying for every time a new emoji is updated,
        #   check every x mins for a change in the data structure that would hold newly uploaded emojis)
        self.new_emoji_set = set()
        # Build a dictionary of all users in the workspace (for determining changes in name, status)
        self.users_dict = {x['id']: x for x in self.st.get_channel_members('CM3E3E82J', True)}
        # This dictionary is for tracking updates to these dicts
        self.user_updates_dict = {}

    def cleanup(self, *args):
        """Runs just before instance is destroyed"""
        notify_block = [
            self.bkb.make_context_section(f'{self.bot_name} died. :death-drops::party-dead::death-drops:')
        ]
        self.st.message_main_channel(blocks=notify_block)
        sys.exit(0)

    def process_incoming_action(self, user: str, channel: str, action: dict) -> Optional:
        """Handles an incoming action (e.g., when a button is clicked)"""
        if action['type'] == 'multi_static_select':
            # Multiselect
            selections = action['selected_options']
            parsed_command = ''
            for selection in selections:
                value = selection['value'].replace('-', ' ')
                if 'all' in value:
                    # Only used for randpick/choose. Results in just the command 'rand(pick|choose)'
                    #   If we're selecting all, we don't need to know any of the other selections.
                    parsed_command = f'{value.split()[0]}'
                    break
                if parsed_command == '':
                    # Put the entire first value into the parsed command (e.g., 'pick 1'
                    parsed_command = f'{value}'
                else:
                    # Build on the already-made command by concatenating the number to the end
                    #   e.g. 'pick 1' => 'pick 12'
                    parsed_command += value.split()[1]

        elif action['type'] == 'button':
            # Normal button clicks just send a 'value' key in the payload dict
            parsed_command = action['value'].replace('-', ' ')
        else:
            # Command not parsed
            # Probably should notify the user, but I'm not sure if Slack will attempt
            #   to send requests multiple times if it doesn't get a response in time.
            return None

    # Basic / Static standalone methods
    # ====================================================
    @staticmethod
    def giggle() -> str:
        """Laughs, uncontrollably at times"""
        # Count the 'no's
        laugh_cycles = randint(1, 500)
        response = f'ti{"hi" * laugh_cycles}!'
        return response

    @staticmethod
    def get_time() -> str:
        """Gets the server time"""
        return f'The server time is `{dt.today():%F %T}`'

    def wfh_epoch(self) -> List[dict]:
        """Calculates WFH epoch time"""
        wfh_epoch = dt(year=2020, month=3, day=3, hour=19, minute=15)
        now = dt.now()
        diff = (now - wfh_epoch)
        wfh_secs = diff.total_seconds()
        strange_units = {
            'dog years_2': (wfh_secs / (60 * 60 * 24)) / 52,
            'hollow months_2': wfh_secs / (60 * 60 * 24 * 29),
            'fortnights_1': wfh_secs / (60 * 60 * 24 * 7 * 2),
            'kilowarhols_1': wfh_secs / (60 * 15000),
            'weeks_1': wfh_secs / (60 * 60 * 24 * 7),
            'sols_1': wfh_secs / (60 * 60 * 24 + 2375),
            'microcenturies_0': wfh_secs / (52 * 60 + 35.76),
            'Kermits_1': wfh_secs / 60 / 14.4,
            'moments_0': wfh_secs / 90,
            'millidays_2': wfh_secs / 86.4,
            'microfortnights_2': wfh_secs * 1.2096,
        }

        units = []
        for k, v in strange_units.items():
            unit, decimals = k.split('_')
            decimals = int(decimals)
            base_txt = f',.{decimals}f'
            txt = '`{{:<20}} {{:>15{}}}`'.format(base_txt).format(f'{unit.title()}:', v)
            units.append(txt)

        unit_txt = '\n'.join(units)
        return [
            self.bkb.make_context_section('WFH Epoch'),
            self.bkb.make_block_section(
                f'Current WFH epoch time is *`{wfh_secs:.0f}`*.'
                f'\n ({diff})',
            ),
            self.bkb.make_context_section(f'{unit_txt}')
        ]

    # Misc. methods
    # ====================================================
    def inspirational(self, channel: str):
        """Sends a random inspirational message"""
        resp = requests.get('https://inspirobot.me/api?generate=true')
        if resp.status_code == 200:
            url = resp.text
            # Download img
            img = requests.get(url)
            if img.status_code == 200:
                with open('/tmp/inspirational.jpg', 'wb') as f:
                    f.write(img.content)
                self.st.upload_file(channel, '/tmp/inspirational.jpg', 'inspirational-shit.jpg')
