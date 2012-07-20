import copy
import os
from FilesystemMonitor import FilesystemMonitor
from Exceptions import TaskError

class ModuleDependency:
    def __init__(self, name, optional = False):
        self._name = name
        self._optional = optional
    def name(self):
        return self._name
    def is_optional(self):
        return self._optional

class Module:
    def __init__(self, name, 
                 source,
                 build,
                 dependencies = [],
                 built_once = False,
                 installed = []):
        self._name = name
        self._dependencies = copy.copy(dependencies)
        self._source = source
        self._build = build
        self._built_once = built_once
        self._installed = installed

    @property
    def installed(self):
        return self._installed
    @installed.setter
    def installed(self, value):
        self._installed = copy.copy(value)

    def _directory(self):
        return self._name

    def _do_download(self, env, source, name):
        srcDirTmp = name
        if source.attribute('module_directory').value :
            srcDirTmp = source.attribute('module_directory').value
            
        env.start_source(name, srcDirTmp)
        
        if os.path.isdir(env.srcdir):
            env.end_source()
        else:
            try:
                source.download(env)
            finally:
                env.end_source()
        for child, child_name in source.children():
            self._do_download(env, child, os.path.join(name, child_name))

    def download(self, env):
        try:
            print(" >> Downloading " + self._name )
            self._do_download(env, self._source, self._name)
            print(" >> Download " + self._name + " - OK ")
            return True
        except TaskError as e:
            print(" >> Download " + self._name + " - Problem ")
            print(e.reason)
            if env.debug :
                import Utils
                Utils.print_backtrace()           
            return False
        except:
            print(" >> Download " + self._name + " - Problem ")
            if env.debug :
                import Utils
                Utils.print_backtrace()
            return False


    def _do_update(self, env, source, name):
        srcDirTmp = name
        if source.attribute('module_directory').value :
            srcDirTmp = source.attribute('module_directory').value
            
        env.start_source(name, srcDirTmp)
        
        try:
            source.update(env)
        finally:
            env.end_source()
        for child, child_name in source.children():
            self._do_update(env, child, os.path.join(name, child_name))

    def update(self, env):
        try:
            self._do_update(env, self._source, self._name)
            print(" Update " + self._name + " - OK ")
            return True
        except TaskError as e:
            print(e.reason)
            if env.debug :
                import Utils
                Utils.print_backtrace()           
            return False
        except:
            if env.debug :
                import Utils
                Utils.print_backtrace()
            return False

    def uninstall(self, env):
        # delete installed files
        for installed in self._installed:
            try:
                os.remove(installed)
            except OSError:
                pass
        # delete directories where files were installed if they are empty
        dirs = [os.path.dirname(installed) for installed in self._installed]
        def uniq(seq):
            keys = {}
            for e in seq:
                keys[e] = 1
            return keys.keys()
        for d in uniq(dirs):
            try:
                os.removedirs(d)
            except OSError:
                pass
        self._installed = []

    def build(self, env, jobs):
        
        self.uninstall(env)
        # delete in case this is a new build configuration
        # and there are old files around
        if not self._built_once:
            self.clean(env)
        # setup the monitor
        monitor = FilesystemMonitor(env.installdir)
        monitor.start()

        srcDirTmp = self._name
        if self._source.attribute('module_directory').value :
            srcDirTmp = self._source.attribute('module_directory').value
            
        env.start_build(self._name, srcDirTmp,
                        self._build.supports_objdir)
        if not os.path.isdir(env.installdir):
            os.mkdir(env.installdir)
        if self._build.supports_objdir and not os.path.isdir(env.objdir):
            os.mkdir(env.objdir)

        try:
            print(" >> Building " + self._name )
            if self.attribute('pre_installation').value != '':
                self.perform_pre_installation(env)
            self._build.threatParamVariables(env)
            self._build.build(env, jobs)
            self._installed = monitor.end()
            env.end_build()
            self._built_once = True
            if self.attribute('post_installation').value != '':
                self.perform_post_installation(env)
            print(" >> Built " + self._name + " - OK ")
            return True
        except TaskError as e:
            print(e.reason)
            if env.debug :
                import Utils
                Utils.print_backtrace()           
            return False
        except:
            self._installed = monitor.end()
            env.end_build()
            if env.debug :
                import Utils
                Utils.print_backtrace()
            return False

    def check_build_version(self, env):
        srcDirTmp = self._name
        if self._source.attribute('module_directory').value :
            srcDirTmp = self._source.attribute('module_directory').value
            
        env.start_build(self._name, srcDirTmp,
                        self._build.supports_objdir)
        
        # this if does not make any sense to me. If you do not have the object
        # dir  the build version is automatically true ?  Even worse if you do
        # NOT have the src dir it is true also????? Does not make any sense!!!
#        if not os.path.isdir(env.objdir) or not os.path.isdir(env.srcdir):
#            retval = True
#        else:
        retval = self._build.check_version(env)
        env.end_build()
        return retval

    def is_downloaded(self, env):
        srcDirTmp = self._name
        if self._source.attribute('module_directory').value :
            srcDirTmp = self._source.attribute('module_directory').value

        env.start_source(self._name,srcDirTmp)
        retval = os.path.isdir(env.srcdir)
        env.end_source()
        return retval

    def check_source_version(self, env):
        srcDirTmp = self._name
        if self._source.attribute('module_directory').value :
            srcDirTmp = self._source.attribute('module_directory').value

        env.start_source(self._name, srcDirTmp)
        retval = self._source.check_version(env)
        env.end_source()
        return retval


    def update_libpath(self, env):
        srcDirTmp = self._name
        if self._source.attribute('module_directory').value :
            srcDirTmp = self._source.attribute('module_directory').value
            
        env.start_build(self._name, srcDirTmp,
                        self._build.supports_objdir)
        env.end_build()

    def clean(self, env):
        srcDirTmp = self._name
        if self._source.attribute('module_directory').value :
            srcDirTmp = self._source.attribute('module_directory').value

        env.start_build(self._name, srcDirTmp,
                        self._build.supports_objdir)
        if not os.path.isdir(env.objdir) or not os.path.isdir(env.srcdir):
            env.end_build()
            return
        try:
            self._build.clean(env)
            env.end_build()
            self._built_once = False
            print(" Clean " + self._name + " - OK ")
            return True
        except TaskError as e:
            print(e.reason)
            if env.debug :
                import Utils
                Utils.print_backtrace()           
            return False
        except:
            env.end_build()
            if env.debug :
                import Utils
                Utils.print_backtrace()
            return False

    def is_built_once(self):
        return self._built_once
    def get_source(self):
        return self._source
    def get_build(self):
        return self._build
    def name(self):
        return self._name
    def dependencies(self):
        return self._dependencies
