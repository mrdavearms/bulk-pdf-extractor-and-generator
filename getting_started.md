# Getting Started

Welcome to the **Bulk PDF Generator**. This guide is the recommended starting point before using the application.

This tool generates pre-filled PDFs from student data in an Excel spreadsheet. Before you can use it effectively, your PDF template needs to have **properly named form fields**.

The steps below walk you through reviewing and preparing your PDF template in **Adobe Acrobat Pro**.

## Step 1: Install Adobe Acrobat Pro

Adobe Acrobat Pro is provided to all **Department of Education and Training** staff at no cost. To install it:

* Open **Adobe Creative Cloud** on your computer. If you don't have it, download it from [Adobe Creative Cloud](https://creativecloud.adobe.com/apps/download/creative-cloud).
* Sign in with your **department credentials** (your DET email and password).
* Find **Adobe Acrobat Pro** in the list of available apps.
* Click **Install** and wait for it to finish.

You need **Acrobat Pro** specifically, not the free Acrobat Reader. Only Pro allows you to edit form fields.

## Step 2: View Existing Form Fields

Before making changes, have a look at what fields are already in your PDF template.

* Open the PDF in **Adobe Acrobat Pro**.
* Move your mouse over the page and click into any light-coloured boxes or checkboxes. These are the form fields.
* Type in text fields, tick checkboxes, or choose items from dropdowns to see how they behave.

## Step 3: Switch to Form Editing Mode

To see all fields at a glance and make changes:

* Open the PDF in **Adobe Acrobat Pro**.
* Go to the **All Tools** or **Tools** tab at the top.
* Click **Prepare Form** (under Forms & Signatures).
* Click **Start**. The document will switch into form editing mode and all fields will show with coloured outlines.

## Step 4: Edit Existing Form Fields

Once you are in **Prepare Form** mode:

* Click once on a field to select it.
* To change its size or position, drag the handles around the field or drag the field itself.
* To change its settings (name, required/optional, read-only, format, etc.):
    * **Double-click** the field, or
    * **Right-click** the field and choose **Properties**.
* In the Properties window, use the tabs:
    * **General** - field name, tooltip, required, read-only.
    * **Appearance** - border, fill, text style.
    * **Options / Format / Validate / Calculate** - extra behaviour, depending on field type.
* Click **Close** in the Properties window when you are finished.

### Naming Fields

**Field names matter.** The generator matches PDF field names to your Excel column headers. Give your fields clear, descriptive names like:

* **Surname** (not "Text1" or "field_42")
* **First name**
* **VCAA student number**
* **School name**

The matching is case-insensitive, so "Surname" will match an Excel column called "surname" or "SURNAME".

## Step 5: Add New Form Fields

Still in **Prepare Form** mode:

* Look at the toolbar at the top of the page.
* Choose the type of field you want (Text field, Checkbox, Radio button, Dropdown, etc.).
* Click on the page where you want the field to appear.
* Adjust size and position if needed, then open **Properties** to configure it (see Step 4 above).

## Step 6: Preview the Form

* While still in **Prepare Form** mode, click **Preview** in the top toolbar.
* Test typing in fields, ticking boxes, and making sure everything behaves correctly.
* Click **Edit** (or exit Preview) to go back to editing.

## Common Gotchas

* **Can't change field settings?** Make sure you have **Prepare Form** selected, not **Edit PDF**. Edit PDF changes page content, not form fields.
* **Field can't be typed into?** It may be set to **Read-only** in its Properties.
* **Fields seem to disappear?** They might be set to **hidden** or **visible but doesn't print** in the field's visibility settings.
* **Combed fields** (individual character boxes like student numbers) are detected automatically by this app. Just make sure each character box has a name like **StudentNumber[0]**, **StudentNumber[1]**, etc.

## Helpful Resources

### Official Adobe Guides

* [Work with Form Fields - Quick Tutorial](https://experienceleague.adobe.com/en/docs/document-cloud-learn/acrobat-learning/advanced-tasks/workforms) - Step-by-step guide showing Prepare Form, editing fields, and previewing.
* [PDF Form Field Properties](https://helpx.adobe.com/nz/acrobat/using/pdf-form-field-properties.html) - Explains what each field property does.

### Video Tutorials

* [Adobe Acrobat Pro: How to Prepare Forms](https://www.youtube.com/watch?v=ZmtSeoF_t4c) - Short walkthrough of adding and editing form fields in Acrobat Pro.

## Next Steps

Once your PDF template has properly named fields:

* Go to the **Analyze Template** tab to scan your PDF and see what fields were detected.
* Or go straight to the **Generate PDFs** tab if you already have a template configuration saved.
