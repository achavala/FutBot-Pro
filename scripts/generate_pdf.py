#!/usr/bin/env python3
"""
Convert PROJECT_VISION_AND_ARCHITECTURE.md to HTML with professional styling.
The HTML can be printed to PDF from any browser (File > Print > Save as PDF).
"""

import markdown
from pathlib import Path
import sys

def markdown_to_html(md_file: str, html_file: str):
    """Convert markdown file to HTML with custom styling for PDF printing."""
    
    # Read markdown file
    md_path = Path(md_file)
    if not md_path.exists():
        print(f"Error: File not found: {md_file}")
        sys.exit(1)
    
    md_content = md_path.read_text(encoding='utf-8')
    
    # Convert markdown to HTML
    html_content = markdown.markdown(
        md_content,
        extensions=['extra', 'codehilite', 'tables', 'toc']
    )
    
    # Custom CSS styling optimized for PDF printing
    css_style = """
    <style>
        @media print {
            @page {
                size: A4;
                margin: 2cm;
            }
            
            body {
                font-size: 11pt;
            }
            
            h1 {
                page-break-after: avoid;
            }
            
            h2, h3 {
                page-break-after: avoid;
            }
            
            pre {
                page-break-inside: avoid;
            }
            
            table {
                page-break-inside: avoid;
            }
        }
        
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #fff;
        }
        
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 30px;
            font-size: 2.2em;
        }
        
        h2 {
            color: #34495e;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
            margin-top: 25px;
            font-size: 1.8em;
        }
        
        h3 {
            color: #555;
            margin-top: 20px;
            font-size: 1.4em;
        }
        
        h4 {
            color: #666;
            margin-top: 15px;
            font-size: 1.2em;
        }
        
        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
            font-size: 0.9em;
            color: #e74c3c;
        }
        
        pre {
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            overflow-x: auto;
            font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
            font-size: 0.85em;
            line-height: 1.4;
        }
        
        pre code {
            background-color: transparent;
            padding: 0;
            color: #333;
        }
        
        blockquote {
            border-left: 4px solid #3498db;
            margin-left: 0;
            padding-left: 20px;
            color: #666;
            font-style: italic;
        }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        
        th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        ul, ol {
            margin: 15px 0;
            padding-left: 30px;
        }
        
        li {
            margin: 8px 0;
        }
        
        a {
            color: #3498db;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        .toc {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 20px;
            margin: 20px 0;
        }
        
        .toc ul {
            list-style-type: none;
            padding-left: 0;
        }
        
        .toc li {
            margin: 8px 0;
        }
        
        .toc a {
            color: #2c3e50;
            font-weight: 500;
        }
        
        hr {
            border: none;
            border-top: 2px solid #ecf0f1;
            margin: 30px 0;
        }
        
        strong {
            color: #2c3e50;
            font-weight: 600;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 30px;
            border-bottom: 3px solid #3498db;
        }
        
        .header h1 {
            border: none;
            font-size: 36pt;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .header h2 {
            border: none;
            font-size: 20pt;
            color: #7f8c8d;
            font-weight: normal;
        }
        
        .header p {
            color: #95a5a6;
            margin-top: 20px;
            font-size: 14pt;
        }
        
        .footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            text-align: center;
            color: #95a5a6;
            font-size: 0.9em;
        }
        
        .print-instructions {
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 30px;
            color: #856404;
        }
        
        .print-instructions strong {
            color: #856404;
        }
    </style>
    """
    
    # Wrap HTML content
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FutBot: Project Vision & Architecture</title>
        {css_style}
    </head>
    <body>
        <div class="print-instructions">
            <strong>📄 To Save as PDF:</strong> Open this file in your browser, then go to <strong>File > Print</strong> 
            and select <strong>"Save as PDF"</strong> as the destination. Make sure to check "Background graphics" 
            in print settings for best results.
        </div>
        
        <div class="header">
            <h1>FutBot</h1>
            <h2>Project Vision, Technical Architecture & Achievements</h2>
            <p>Production-Grade Regime-Aware Trading System</p>
        </div>
        
        {html_content}
        
        <div class="footer">
            <p><strong>Document Version:</strong> 1.0 | <strong>Last Updated:</strong> 2024-11-24</p>
            <p>FutBot Development Team</p>
        </div>
    </body>
    </html>
    """
    
    # Write HTML file
    html_path = Path(html_file)
    html_path.write_text(full_html, encoding='utf-8')
    print(f"✅ HTML file created successfully: {html_file}")
    print(f"\n📄 To convert to PDF:")
    print(f"   1. Open {html_file} in your web browser")
    print(f"   2. Go to File > Print (or Cmd+P / Ctrl+P)")
    print(f"   3. Select 'Save as PDF' as the destination")
    print(f"   4. Click 'Save'")
    return True

if __name__ == "__main__":
    # Default paths
    md_file = "PROJECT_VISION_AND_ARCHITECTURE.md"
    html_file = "PROJECT_VISION_AND_ARCHITECTURE.html"
    
    # Allow command line arguments
    if len(sys.argv) > 1:
        md_file = sys.argv[1]
    if len(sys.argv) > 2:
        html_file = sys.argv[2]
    
    success = markdown_to_html(md_file, html_file)
    sys.exit(0 if success else 1)
