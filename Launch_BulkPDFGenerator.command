#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python pdf_generator.py
