=================
Convert data in a dataset
=================

This tutorial will guide you through the process of converting data in a dataset.
With the converter, you can:

* Normalize data
* Encode categorical data
* Convert data types
* And more!


Prerequisites
-------------
Before starting, make sure you have:

* A dataset in DashAI

Step-by-Step Guide
------------------

1. Access the dataset section
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: ../tutorials/images/converter/step1.png
   :alt: Navigate to dataset section
   :width: 600

Navigate to the dataset section in DashAI to access the dataset you want to convert.

2. Open the converter modal
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: ../tutorials/images/converter/step2.png
   :alt: Open converter modal
   :width: 600

* Click on the settings icon of the dataset you want to convert.
A summary of the dataset will appear, along with an empty table where your converters will be listed.

3. Select the converter
~~~~~~~~~~~~~~~~~~~~~~~

.. image:: ../tutorials/images/converter/step3.png
   :alt: Select converter
   :width: 600

* Click the "Add" button to open the list of available converters.
* Use the search bar to find a specific converter, and click on its name to view a description.
* Click "Add" to include the selected converter in the table.

4. Configure the converter
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: ../tutorials/images/converter/step4.png
   :alt: Configure converter
   :width: 600

* Click the settings icon next to the converter you want to configure.
* Adjust the necessary parameters for the conversion.
* Click "Save" to apply the settings.

5. Set the scope of the converter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: ../tutorials/images/converter/step5.png
   :alt: Set scope of converter
   :width: 600

By default, the converter processes all columns and rows in the dataset. 
However, you can select specific columns to transform and the number of rows to learn from.

To refine the scope of the converter:

* Click the three-column icon next to the converter to set its scope.
* Select the specific columns you want to transform.
* Define the number of rows the converter should learn from.
* Click "Save" to apply these settings.

6. Set the target column
~~~~~~~~~~~~~~~~~~~~~~~

.. image:: ../tutorials/images/converter/step6.png
   :alt: Set target column
   :width: 600

Some converters require a target column to learn from.
This column can be labeled as "class" or "target" in the dataset.

* Select the text field above the list of converters.
* Set the target column index.

7. Start the conversion
~~~~~~~~~~~~~~~~~~~~~~

.. image:: ../tutorials/images/converter/step7.png
   :alt: Start conversion
   :width: 600

* Click the "Modify" button to begin the conversion process.

Once the conversion starts, you will see the results in the dataset summary.

By following these steps, you can efficiently convert your dataset into the desired format within DashAI.

Tips and Best Practices
------------------------

* You can use the Exploration module to navigate through the dataset and see the data you need to convert.
* Start with a simple conversion and gradually add more converters andcomplex transformations.
* Ensure your converter is properly configured to achieve the desired output.
* The converter will try to modify the data in place, only adding new columns at the end of the dataset when required.
* Ensure the converter is compatible with the type of data you selected for the conversion.
* Verify the conversion results to ensure the desired output is achieved.

Troubleshooting
---------------

* Common issues:
    - Missing target column index for supervised converters
    - Incompatible data types
    - Converter does not converge due to its parameters