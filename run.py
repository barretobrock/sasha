#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
os.environ['SASHA_DEBUG'] = "0"
from sasha.app import app


@app.route('/sasha')
def index():
    return 'SASHA'


if __name__ == '__main__':
    app.run(port=5003)


