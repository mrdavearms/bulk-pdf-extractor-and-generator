#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python vcaa_pdf_generator_v2.py
