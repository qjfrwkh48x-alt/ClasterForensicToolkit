"""
Claster Forensic Toolkit - Reporting Module

Generates professional forensic reports in multiple formats (HTML, PDF, DOCX, CSV, JSON).
Supports chain of custody, hash verification, timelines, evidence export, and digital signatures.
"""

from claster.report.generators import (
    generate_html_report,
    generate_pdf_report,
    generate_docx_report,
    generate_csv_report,
    generate_json_report,
    add_timeline,
    export_report_with_evidence,
)
from claster.report.custody import (
    add_chain_of_custody,
    add_hash_verification,
)
from claster.report.sign import sign_report

__all__ = [
    'generate_html_report',
    'generate_pdf_report',
    'generate_docx_report',
    'generate_csv_report',
    'generate_json_report',
    'add_chain_of_custody',
    'add_hash_verification',
    'add_timeline',
    'export_report_with_evidence',
    'sign_report',
]