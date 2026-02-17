#!/usr/bin/env python3
"""
VCAA Evidence Application PDF Generator
A GUI application to batch-fill VCAA Special Examination Arrangements forms.

For Wangaratta High School - 2026
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import pandas as pd
from pypdf import PdfReader, PdfWriter
import threading


class VCAAPDFGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("VCAA Evidence Application Generator")
        self.root.geometry("900x750")
        self.root.minsize(800, 650)
        
        # File paths
        self.pdf_template_path = tk.StringVar()
        self.excel_file_path = tk.StringVar()
        
        # Data
        self.df = None
        self.pdf_fields = []
        self.selected_rows = {}  # Dictionary to track selected rows {tree_item_id: row_index}
        
        # Critical fields for validation
        self.critical_fields = ['surname', 'first name', 'vcaa student number']
        
        self.setup_ui()
    
    def setup_ui(self):
        """Create the main UI layout."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="VCAA Evidence Application Generator",
            font=('Helvetica', 18, 'bold')
        )
        title_label.pack(pady=(0, 5))
        
        subtitle_label = ttk.Label(
            main_frame,
            text="Wangaratta High School - 2026",
            font=('Helvetica', 12)
        )
        subtitle_label.pack(pady=(0, 15))
        
        # File Selection Frame
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        # PDF Template selection
        pdf_row = ttk.Frame(file_frame)
        pdf_row.pack(fill=tk.X, pady=5)
        ttk.Label(pdf_row, text="PDF Template:", width=15).pack(side=tk.LEFT)
        ttk.Entry(pdf_row, textvariable=self.pdf_template_path, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(pdf_row, text="Browse...", command=self.select_pdf).pack(side=tk.LEFT)
        
        # Excel file selection
        excel_row = ttk.Frame(file_frame)
        excel_row.pack(fill=tk.X, pady=5)
        ttk.Label(excel_row, text="Excel Data File:", width=15).pack(side=tk.LEFT)
        ttk.Entry(excel_row, textvariable=self.excel_file_path, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(excel_row, text="Browse...", command=self.select_excel).pack(side=tk.LEFT)
        
        # Load button
        ttk.Button(file_frame, text="Load & Preview Data", command=self.load_data).pack(pady=10)
        
        # Validation Frame
        self.validation_frame = ttk.LabelFrame(main_frame, text="Validation Warnings", padding="10")
        self.validation_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.validation_text = tk.Text(self.validation_frame, height=3, wrap=tk.WORD, state=tk.DISABLED)
        self.validation_text.pack(fill=tk.X)
        
        # Selection Controls Frame
        selection_frame = ttk.Frame(main_frame)
        selection_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(selection_frame, text="Select students to process:", font=('Helvetica', 11, 'bold')).pack(side=tk.LEFT)
        
        ttk.Button(selection_frame, text="Select All", command=self.select_all).pack(side=tk.LEFT, padx=(15, 5))
        ttk.Button(selection_frame, text="Deselect All", command=self.deselect_all).pack(side=tk.LEFT, padx=5)
        
        self.selection_count_label = ttk.Label(selection_frame, text="")
        self.selection_count_label.pack(side=tk.RIGHT)
        
        # Preview Frame
        preview_frame = ttk.LabelFrame(main_frame, text="Student Preview (click to select/deselect)", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Treeview for student list with checkbox column
        columns = ('selected', 'row', 'surname', 'first_name', 'student_number', 'status')
        self.tree = ttk.Treeview(preview_frame, columns=columns, show='headings', height=12)
        
        self.tree.heading('selected', text='✓')
        self.tree.heading('row', text='#')
        self.tree.heading('surname', text='Surname')
        self.tree.heading('first_name', text='First Name')
        self.tree.heading('student_number', text='VCAA Number')
        self.tree.heading('status', text='Status')
        
        self.tree.column('selected', width=40, anchor='center')
        self.tree.column('row', width=40, anchor='center')
        self.tree.column('surname', width=140)
        self.tree.column('first_name', width=140)
        self.tree.column('student_number', width=110)
        self.tree.column('status', width=180)
        
        # Bind click event for toggling selection
        self.tree.bind('<ButtonRelease-1>', self.toggle_selection)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Summary label
        self.summary_label = ttk.Label(main_frame, text="No data loaded", font=('Helvetica', 11))
        self.summary_label.pack(pady=5)
        
        # Progress Frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="")
        self.progress_label.pack()
        
        # Generate Button
        self.generate_btn = ttk.Button(
            main_frame, 
            text="Generate PDFs for Selected Students", 
            command=self.start_generation,
            state=tk.DISABLED
        )
        self.generate_btn.pack(pady=10)
    
    def select_pdf(self):
        """Open file dialog to select PDF template."""
        filepath = filedialog.askopenfilename(
            title="Select VCAA PDF Template",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if filepath:
            self.pdf_template_path.set(filepath)
    
    def select_excel(self):
        """Open file dialog to select Excel data file."""
        filepath = filedialog.askopenfilename(
            title="Select Student Data Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filepath:
            self.excel_file_path.set(filepath)
    
    def load_data(self):
        """Load the Excel data and PDF template, then show preview."""
        pdf_path = self.pdf_template_path.get()
        excel_path = self.excel_file_path.get()
        
        # Validate paths
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showerror("Error", "Please select a valid PDF template file.")
            return
        
        if not excel_path or not os.path.exists(excel_path):
            messagebox.showerror("Error", "Please select a valid Excel data file.")
            return
        
        try:
            # Load PDF and get field names
            reader = PdfReader(pdf_path)
            fields = reader.get_fields()
            if fields:
                self.pdf_fields = list(fields.keys())
            else:
                messagebox.showerror("Error", "The PDF template has no fillable form fields.")
                return
            
            # Load Excel data
            if excel_path.endswith('.csv'):
                self.df = pd.read_csv(excel_path)
            else:
                self.df = pd.read_excel(excel_path)
            
            # Clean column names (strip whitespace, lowercase for matching)
            self.df.columns = [str(col).strip() for col in self.df.columns]
            
            # Create lowercase mapping for field matching
            self.column_mapping = {col.lower(): col for col in self.df.columns}
            self.field_mapping = {field.lower(): field for field in self.pdf_fields}
            
            # Clear previous selections
            self.selected_rows = {}
            
            # Validate and show preview
            self.validate_data()
            self.show_preview()
            
            # Select all by default
            self.select_all()
            
            # Enable generate button
            self.generate_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data:\n{str(e)}")
    
    def validate_data(self):
        """Check for missing critical fields and show warnings."""
        warnings = []
        
        # Check each row for critical fields
        for idx, row in self.df.iterrows():
            row_warnings = []
            row_dict = {str(col).lower(): val for col, val in row.items()}
            
            for field in self.critical_fields:
                val = row_dict.get(field, '')
                if pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan':
                    row_warnings.append(field)
            
            if row_warnings:
                surname = row_dict.get('surname', f'Row {idx+1}')
                if pd.isna(surname) or str(surname).strip() == '':
                    surname = f'Row {idx+1}'
                warnings.append(f"• {surname}: Missing {', '.join(row_warnings)}")
        
        # Display warnings
        self.validation_text.config(state=tk.NORMAL)
        self.validation_text.delete(1.0, tk.END)
        
        if warnings:
            warning_text = f"⚠️ {len(warnings)} student(s) have missing critical fields:\n"
            warning_text += "\n".join(warnings[:10])  # Show first 10
            if len(warnings) > 10:
                warning_text += f"\n... and {len(warnings) - 10} more"
            self.validation_text.insert(1.0, warning_text)
            self.validation_text.config(foreground='#B8860B')
        else:
            self.validation_text.insert(1.0, "✓ All students have required fields populated.")
            self.validation_text.config(foreground='green')
        
        self.validation_text.config(state=tk.DISABLED)
    
    def show_preview(self):
        """Display the student data in the preview treeview."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Reset selected rows tracking
        self.selected_rows = {}
        
        # Add students to preview
        valid_count = 0
        warning_count = 0
        
        for idx, row in self.df.iterrows():
            row_dict = {str(col).lower(): val for col, val in row.items()}
            
            surname = str(row_dict.get('surname', '')).strip()
            first_name = str(row_dict.get('first name', '')).strip()
            student_num = str(row_dict.get('vcaa student number', '')).strip()
            
            # Skip completely empty rows
            if (pd.isna(row_dict.get('surname')) or surname == '' or surname.lower() == 'nan'):
                continue
            
            # Check status
            missing = []
            for field in self.critical_fields:
                val = row_dict.get(field, '')
                if pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan':
                    missing.append(field)
            
            if missing:
                status = f"⚠️ Missing: {', '.join(missing)}"
                warning_count += 1
            else:
                status = "✓ Ready"
                valid_count += 1
            
            # Clean display values
            if surname.lower() == 'nan':
                surname = ''
            if first_name.lower() == 'nan':
                first_name = ''
            if student_num.lower() == 'nan':
                student_num = ''
            
            # Insert with empty checkbox initially
            item_id = self.tree.insert('', tk.END, values=('☐', idx+1, surname, first_name, student_num, status))
            # Store mapping of item_id to dataframe index
            self.selected_rows[item_id] = {'index': idx, 'selected': False}
        
        # Update summary
        total = valid_count + warning_count
        self.summary_label.config(
            text=f"Loaded {total} students: {valid_count} ready, {warning_count} with warnings"
        )
        
        self.update_selection_count()
    
    def toggle_selection(self, event):
        """Toggle selection of a row when clicked."""
        item = self.tree.identify_row(event.y)
        if item and item in self.selected_rows:
            # Toggle the selection
            self.selected_rows[item]['selected'] = not self.selected_rows[item]['selected']
            
            # Update the checkbox display
            current_values = list(self.tree.item(item, 'values'))
            current_values[0] = '☑' if self.selected_rows[item]['selected'] else '☐'
            self.tree.item(item, values=current_values)
            
            self.update_selection_count()
    
    def select_all(self):
        """Select all students."""
        for item_id in self.selected_rows:
            self.selected_rows[item_id]['selected'] = True
            current_values = list(self.tree.item(item_id, 'values'))
            current_values[0] = '☑'
            self.tree.item(item_id, values=current_values)
        
        self.update_selection_count()
    
    def deselect_all(self):
        """Deselect all students."""
        for item_id in self.selected_rows:
            self.selected_rows[item_id]['selected'] = False
            current_values = list(self.tree.item(item_id, 'values'))
            current_values[0] = '☐'
            self.tree.item(item_id, values=current_values)
        
        self.update_selection_count()
    
    def update_selection_count(self):
        """Update the selection count label."""
        selected = sum(1 for item in self.selected_rows.values() if item['selected'])
        total = len(self.selected_rows)
        self.selection_count_label.config(text=f"Selected: {selected} of {total}")
        
        # Update button text
        if selected == 0:
            self.generate_btn.config(text="Generate PDFs (none selected)", state=tk.DISABLED)
        elif selected == 1:
            self.generate_btn.config(text="Generate PDF for 1 Student", state=tk.NORMAL)
        else:
            self.generate_btn.config(text=f"Generate PDFs for {selected} Students", state=tk.NORMAL)
    
    def format_value(self, val):
        """Format a value for PDF insertion, handling dates and empty values."""
        if pd.isna(val):
            return ""
        
        # Handle datetime objects (Australian format)
        if isinstance(val, (datetime, pd.Timestamp)):
            return val.strftime('%d/%m/%Y')
        
        # Convert to string and clean
        str_val = str(val).strip()
        if str_val.lower() == 'nan':
            return ""
        
        return str_val
    
    def generate_pdf(self, row_data, output_path):
        """Generate a single filled PDF from the template."""
        reader = PdfReader(self.pdf_template_path.get())
        writer = PdfWriter()
        
        # Clone the PDF
        writer.append(reader)
        
        # Create a dictionary of field values to fill
        field_values = {}
        
        # Map Excel columns to PDF fields (case-insensitive matching)
        row_dict_lower = {str(col).lower(): val for col, val in row_data.items()}
        
        for pdf_field in self.pdf_fields:
            pdf_field_lower = pdf_field.lower()
            
            # Try to find matching Excel column
            if pdf_field_lower in row_dict_lower:
                val = self.format_value(row_dict_lower[pdf_field_lower])
                field_values[pdf_field] = val
        
        # Fill all pages
        for page in writer.pages:
            writer.update_page_form_field_values(page, field_values)
        
        # Save the filled PDF
        with open(output_path, 'wb') as f:
            writer.write(f)
    
    def start_generation(self):
        """Start the PDF generation process in a background thread."""
        # Check if any students are selected
        selected_count = sum(1 for item in self.selected_rows.values() if item['selected'])
        if selected_count == 0:
            messagebox.showwarning("No Selection", "Please select at least one student to generate PDFs.")
            return
        
        # Disable button during generation
        self.generate_btn.config(state=tk.DISABLED)
        
        # Start generation in background thread
        thread = threading.Thread(target=self.run_generation)
        thread.start()
    
    def run_generation(self):
        """Run the actual PDF generation process."""
        try:
            # Create output folder
            excel_dir = os.path.dirname(self.excel_file_path.get())
            output_folder = os.path.join(excel_dir, "Completed Applications")
            os.makedirs(output_folder, exist_ok=True)
            
            # Get only selected rows
            selected_indices = [
                item['index'] for item in self.selected_rows.values() 
                if item['selected']
            ]
            
            total = len(selected_indices)
            success_count = 0
            error_count = 0
            
            for i, idx in enumerate(selected_indices):
                row = self.df.iloc[idx]
                row_dict = {str(col).lower(): val for col, val in row.items()}
                
                # Get name for filename
                first_name = str(row_dict.get('first name', 'Unknown')).strip()
                surname = str(row_dict.get('surname', 'Unknown')).strip()
                
                if first_name.lower() == 'nan':
                    first_name = 'Unknown'
                if surname.lower() == 'nan':
                    surname = 'Unknown'
                
                # Clean names for filename (remove invalid characters)
                safe_first = "".join(c for c in first_name if c.isalnum() or c in ' -_').strip()
                safe_surname = "".join(c for c in surname if c.isalnum() or c in ' -_').strip()
                
                # Create filename
                filename = f"{safe_first}_{safe_surname}_Evidence Application Wangaratta High School 2026.pdf"
                output_path = os.path.join(output_folder, filename)
                
                try:
                    self.generate_pdf(row, output_path)
                    success_count += 1
                    status_text = f"Created: {filename}"
                except Exception as e:
                    error_count += 1
                    status_text = f"Error: {surname} - {str(e)}"
                
                # Update progress
                progress = ((i + 1) / total) * 100
                self.root.after(0, self.update_progress, progress, status_text, i+1, total)
            
            # Final message
            final_message = f"Complete! {success_count} PDFs created"
            if error_count > 0:
                final_message += f", {error_count} errors"
            final_message += f"\n\nOutput folder: {output_folder}"
            
            self.root.after(0, self.generation_complete, final_message, output_folder)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Generation failed:\n{str(e)}"))
            self.root.after(0, lambda: self.generate_btn.config(state=tk.NORMAL))
    
    def update_progress(self, progress, status, current, total):
        """Update the progress bar and label."""
        self.progress_var.set(progress)
        self.progress_label.config(text=f"[{current}/{total}] {status}")
    
    def generation_complete(self, message, output_folder):
        """Handle generation completion."""
        self.progress_label.config(text="Generation complete!")
        self.update_selection_count()  # Re-enable button with correct state
        
        # Ask to open folder
        result = messagebox.askyesno(
            "Generation Complete",
            f"{message}\n\nWould you like to open the output folder?"
        )
        
        if result:
            # Open folder in Finder (Mac) or Explorer (Windows)
            import subprocess
            import sys
            
            if sys.platform == 'darwin':  # Mac
                subprocess.run(['open', output_folder])
            elif sys.platform == 'win32':  # Windows
                subprocess.run(['explorer', output_folder])
            else:  # Linux
                subprocess.run(['xdg-open', output_folder])


def main():
    root = tk.Tk()
    
    # Set app icon and style
    style = ttk.Style()
    style.theme_use('clam')  # Use a modern-looking theme
    
    app = VCAAPDFGenerator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
