"""
Export functionality for admin reports.

Generates CSV and PDF exports for jobs, workers, and applications.
"""

import csv
import io
from datetime import datetime
from typing import List, Dict, Any
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas


def export_to_csv(data: List[Dict[str, Any]], filename: str, fields: List[str] = None) -> HttpResponse:
    """
    Export data to CSV file.
    
    Args:
        data: List of dictionaries to export
        filename: Name of the file (without extension)
        fields: List of fields to include (default: all)
        
    Returns:
        HttpResponse with CSV content
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    if not data:
        return response
    
    # Use provided fields or all keys from first item
    if fields is None:
        fields = list(data[0].keys())
    
    writer = csv.DictWriter(response, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    
    for row in data:
        # Convert any complex types to strings
        clean_row = {k: str(v) if not isinstance(v, (str, int, float, type(None))) else v 
                     for k, v in row.items()}
        writer.writerow(clean_row)
    
    return response


def export_to_pdf(
    title: str,
    data: List[Dict[str, Any]],
    filename: str,
    columns: List[Dict[str, str]] = None,
    page_size=letter
) -> HttpResponse:
    """
    Export data to PDF file.
    
    Args:
        title: Report title
        data: List of dictionaries to export
        filename: Name of the file (without extension)
        columns: List of dicts with 'field' and 'header' keys
        page_size: PDF page size (default: letter)
        
    Returns:
        HttpResponse with PDF content
    """
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}_{datetime.now().strftime("%Y%m%d")}.pdf"'
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        alignment=1  # Center
    )
    elements.append(Paragraph(title, title_style))
    
    # Timestamp
    timestamp_style = ParagraphStyle(
        'Timestamp',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=1
    )
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", timestamp_style))
    elements.append(Spacer(1, 20))
    
    if not data:
        elements.append(Paragraph("No data available.", styles['Normal']))
        doc.build(elements)
        response.write(buffer.getvalue())
        buffer.close()
        return response
    
    # Determine columns
    if columns is None:
        fields = list(data[0].keys())
        columns = [{'field': f, 'header': f.replace('_', ' ').title()} for f in fields]
    
    # Build table data
    table_data = [[col['header'] for col in columns]]  # Header row
    
    for row in data:
        table_row = []
        for col in columns:
            value = row.get(col['field'], '')
            # Truncate long values
            str_value = str(value) if value is not None else ''
            if len(str_value) > 50:
                str_value = str_value[:47] + '...'
            table_row.append(str_value)
        table_data.append(table_row)
    
    # Create table
    col_widths = [doc.width / len(columns)] * len(columns)
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Style table
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Body styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2c3e50')),
    ]))
    
    elements.append(table)
    
    # Add summary
    elements.append(Spacer(1, 20))
    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
    )
    elements.append(Paragraph(f"Total records: {len(data)}", summary_style))
    
    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    
    return response


# Pre-built export configurations
class ExportConfigs:
    """Pre-defined export configurations for common reports."""
    
    JOBS_COLUMNS = [
        {'field': 'id', 'header': 'ID'},
        {'field': 'title', 'header': 'Title'},
        {'field': 'status', 'header': 'Status'},
        {'field': 'location', 'header': 'Location'},
        {'field': 'budget', 'header': 'Budget'},
        {'field': 'created_at', 'header': 'Created'},
    ]
    
    WORKERS_COLUMNS = [
        {'field': 'id', 'header': 'ID'},
        {'field': 'name', 'header': 'Name'},
        {'field': 'email', 'header': 'Email'},
        {'field': 'phone', 'header': 'Phone'},
        {'field': 'rating', 'header': 'Rating'},
        {'field': 'is_available', 'header': 'Available'},
        {'field': 'is_verified', 'header': 'Verified'},
    ]
    
    APPLICATIONS_COLUMNS = [
        {'field': 'id', 'header': 'ID'},
        {'field': 'job_title', 'header': 'Job'},
        {'field': 'worker_name', 'header': 'Worker'},
        {'field': 'status', 'header': 'Status'},
        {'field': 'applied_at', 'header': 'Applied'},
    ]
    
    USERS_COLUMNS = [
        {'field': 'id', 'header': 'ID'},
        {'field': 'email', 'header': 'Email'},
        {'field': 'first_name', 'header': 'First Name'},
        {'field': 'last_name', 'header': 'Last Name'},
        {'field': 'user_type', 'header': 'Type'},
        {'field': 'date_joined', 'header': 'Joined'},
        {'field': 'is_active', 'header': 'Active'},
    ]
