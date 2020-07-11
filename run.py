#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
os.environ['VIKTOR_DEBUG'] = "0"
from viktor.app import app


@app.route('/viktor')
def index():
    return 'VIKTOR'


if __name__ == '__main__':
    app.run(port=5003)

