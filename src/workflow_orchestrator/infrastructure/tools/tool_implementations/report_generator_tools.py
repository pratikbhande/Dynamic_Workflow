from langchain_core.tools import Tool
from typing import List
import os
from ....config import settings
import json

def create_report_generator_tools() -> List[Tool]:
    """Create tools for generating reports with diagrams"""
    
    def generate_pdf_report_func(input_str: str) -> str:
        """
        Generate a professional PDF report with charts
        
        Input format (JSON):
        {
            "title": "Report Title",
            "sections": [
                {"heading": "Section 1", "content": "text..."},
                {"heading": "Section 2", "content": "text..."}
            ],
            "charts": [
                {"type": "bar", "data": {...}, "title": "Chart 1"}
            ]
        }
        """
        try:
            # Parse input
            report_data = json.loads(input_str)
            
            # Generate unique filename
            import uuid
            filename = f"report_{uuid.uuid4().hex[:8]}.pdf"
            filepath = os.path.join(settings.UPLOAD_DIR, filename)
            
            # Create PDF
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
            
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor='#1a1a1a',
                spaceAfter=30,
                alignment=TA_CENTER
            )
            story.append(Paragraph(report_data.get('title', 'Report'), title_style))
            story.append(Spacer(1, 0.5*inch))
            
            # Generate charts if requested
            chart_files = []
            if 'charts' in report_data:
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('Agg')
                
                for idx, chart_spec in enumerate(report_data['charts']):
                    chart_file = os.path.join(settings.UPLOAD_DIR, f"chart_{idx}_{uuid.uuid4().hex[:8]}.png")
                    
                    plt.figure(figsize=(10, 6))
                    
                    if chart_spec['type'] == 'bar':
                        plt.bar(chart_spec['data'].keys(), chart_spec['data'].values())
                    elif chart_spec['type'] == 'line':
                        plt.plot(list(chart_spec['data'].keys()), list(chart_spec['data'].values()))
                    elif chart_spec['type'] == 'pie':
                        plt.pie(chart_spec['data'].values(), labels=chart_spec['data'].keys(), autopct='%1.1f%%')
                    
                    plt.title(chart_spec.get('title', f'Chart {idx+1}'))
                    plt.tight_layout()
                    plt.savefig(chart_file, dpi=300, bbox_inches='tight')
                    plt.close()
                    
                    chart_files.append(chart_file)
            
            # Add sections
            for section in report_data.get('sections', []):
                # Section heading
                story.append(Paragraph(section['heading'], styles['Heading2']))
                story.append(Spacer(1, 0.2*inch))
                
                # Section content
                story.append(Paragraph(section['content'], styles['BodyText']))
                story.append(Spacer(1, 0.3*inch))
            
            # Add charts
            for chart_file in chart_files:
                story.append(Image(chart_file, width=6*inch, height=4*inch))
                story.append(Spacer(1, 0.3*inch))
            
            # Build PDF
            doc.build(story)
            
            # Cleanup chart files
            for chart_file in chart_files:
                if os.path.exists(chart_file):
                    os.remove(chart_file)
            
            return f"""✅ PDF Report generated successfully!

File: {filename}
Path: {filepath}

The report includes:
- {len(report_data.get('sections', []))} sections
- {len(chart_files)} charts/diagrams

Download the report from: {filepath}
"""
        
        except Exception as e:
            return f"❌ Error generating PDF report: {str(e)}"
    
    def generate_charts_func(input_str: str) -> str:
        """
        Generate charts/diagrams from data
        
        Input format (JSON):
        {
            "charts": [
                {
                    "type": "bar|line|pie|scatter",
                    "data": {"label1": value1, "label2": value2},
                    "title": "Chart Title",
                    "filename": "chart_name.png"
                }
            ]
        }
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')
            
            chart_data = json.loads(input_str)
            generated_files = []
            
            for chart_spec in chart_data.get('charts', []):
                filename = chart_spec.get('filename', f"chart_{len(generated_files)}.png")
                filepath = os.path.join(settings.UPLOAD_DIR, filename)
                
                plt.figure(figsize=(10, 6))
                
                chart_type = chart_spec['type']
                data = chart_spec['data']
                
                if chart_type == 'bar':
                    plt.bar(data.keys(), data.values())
                elif chart_type == 'line':
                    plt.plot(list(data.keys()), list(data.values()), marker='o')
                elif chart_type == 'pie':
                    plt.pie(data.values(), labels=data.keys(), autopct='%1.1f%%')
                elif chart_type == 'scatter':
                    plt.scatter(list(data.keys()), list(data.values()))
                
                plt.title(chart_spec.get('title', 'Chart'))
                plt.tight_layout()
                plt.savefig(filepath, dpi=300, bbox_inches='tight')
                plt.close()
                
                generated_files.append(filepath)
            
            result = [f"✅ Generated {len(generated_files)} charts:\n"]
            for filepath in generated_files:
                result.append(f"  - {filepath}")
            
            return "\n".join(result)
        
        except Exception as e:
            return f"❌ Error generating charts: {str(e)}"
    
    return [
        Tool(
            name="generate_pdf_report",
            description="""Generate a professional PDF report with sections and charts.
            
Input must be JSON with:
- title: Report title
- sections: Array of {heading, content}
- charts (optional): Array of {type, data, title}

Example:
{
  "title": "Sales Analysis Report",
  "sections": [
    {"heading": "Executive Summary", "content": "..."},
    {"heading": "Detailed Analysis", "content": "..."}
  ],
  "charts": [
    {"type": "bar", "data": {"Q1": 100, "Q2": 150}, "title": "Quarterly Sales"}
  ]
}
""",
            func=generate_pdf_report_func
        ),
        Tool(
            name="generate_charts",
            description="""Generate charts/diagrams from data.
            
Supported types: bar, line, pie, scatter

Input must be JSON:
{
  "charts": [
    {
      "type": "bar",
      "data": {"Label1": 10, "Label2": 20},
      "title": "My Chart",
      "filename": "mychart.png"
    }
  ]
}
""",
            func=generate_charts_func
        )
    ]