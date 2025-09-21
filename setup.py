from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import shutil, site, os

class BuildAndCopy(build_ext):
    def run(self):
        super().run()
        for ext in self.extensions:
            filename = self.get_ext_filename(ext.name)
            build_path = os.path.join(self.build_lib, filename)
            target_dir = site.getsitepackages()[0]
            try:
                shutil.copy(build_path, target_dir)
                print(f"✅ Installed {filename} into {target_dir}")
            except Exception as e:
                print(f"⚠️ Could not auto-install extension: {e}")

setup(
    name="search_rng_module",
    ext_modules=[Extension("search_rng_module", ["search_rng_module.c"])],
    cmdclass={"build_ext": BuildAndCopy},
)