Plugin (``profiler_plugin``)
============================

The QGIS Profiler Plugin provides the UI layer on top of the
:doc:`core library </core/index>`. It integrates into the QGIS Development Tools
panel, extending the built-in profiler with additional controls and features.

**Package:** ``profiler-qgis-plugin`` (PyPI) / ``profiler_plugin`` (import)

Using the Core Library Without the Plugin
------------------------------------------

The core library (``qgis_profiler``) can be used independently of the plugin.
This is useful when you want to add profiling to your own plugin without
depending on the UI plugin being installed:

.. code-block:: python

   # In your plugin's pyproject.toml or requirements
   # dependencies = ["profiler-qgis-core"]

   from qgis_profiler.decorators import profile, profile_class
   from qgis_profiler.profiler import ProfilerWrapper

   @profile_class(group="My Plugin")
   class MyPluginLogic:
       def load_data(self):
           pass

       def process(self):
           pass

.. toctree::
   :maxdepth: 2

   plugin
   extension
   settings_dialog
   proxy_model
