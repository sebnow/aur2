#!/usr/bin/env python
import os
import subprocess

class InavlidPackage(Exception):
    pass

class Package:
    """Representation of an Archlinux package"""
    def __init__(self, file):
        self._data = {}
        self.load(file)

    def load(self, file):
        """Load a PKGBUILD (can be within a tar file) and load the variables"""
        script_dir = os.path.dirname(__file__)
        if not script_dir:
            script_dir = os.path.abspath(script_dir)
        is_temporary = False

        # Check if it's a tarballed PKGBUILD and extract it
        if file.endswith('.tar.gz'):
            import tarfile
            import tempfile
            try:
                tar = tarfile.open(file, "r")
            except:
                raise
            else:
                to_extract = None
                for member in tar.getnames():
                    if member.find("PKGBUILD") >= 0:
                        to_extract = member
                        break
                if not to_extract:
                    raise InavlidPackage('tar file does not contain a PKGBUILD')
                directory = tempfile.mkdtemp()
                tar.extract(to_extract, directory)
                file = os.path.join(directory, to_extract)
                is_temporary = True

        # Find the current directory and filename
        working_dir = os.path.dirname(file)
        if working_dir == '':
            working_dir = None
        filename = os.path.basename(file)

        # Let's parse the PKGBUILD
        process = subprocess.Popen([
            os.path.join(script_dir, 'parsepkgbuild.sh'), filename],
            stdout=subprocess.PIPE, cwd=working_dir)
        process.wait()

        if process.returncode != 0:
            raise InavlidPackage("missing variables")

        # "Import" variables into local namespace
        for expression in process.stdout.readlines():
            exec 'temp = dict(' + expression.rstrip() + ')'
            self._data.update(temp)

        # Remove the temporary file since we don't need it
        if is_temporary:
            os.remove(file)
            #os.removedirs(directory)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, item):
        return self._data.__contains__(item)

    def keys(self):
        return self._data.keys()

    def __str__(self):
        return str(self._data)

    def __unicode__(self):
        return unicode(self._data)
