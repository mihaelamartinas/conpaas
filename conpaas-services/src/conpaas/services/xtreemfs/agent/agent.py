# -*- coding: utf-8 -*-

"""
    :copyright: (C) 2010-2013 by Contrail Consortium.
"""

from os.path import exists, join
from os import makedirs, remove

from conpaas.core.expose import expose
from conpaas.core.https.server import HttpJsonResponse, HttpErrorResponse
from conpaas.core.https.server import HttpFileDownloadResponse
from conpaas.services.xtreemfs.agent import role    
from conpaas.core.agent import BaseAgent, AgentException
from conpaas.core.misc import run_cmd

from threading import Lock
import pickle
import base64

class XtreemFSAgent(BaseAgent):
    def __init__(self,
                 config_parser, # config file
                 **kwargs):     # anything you can't send in config_parser 
                                # (hopefully the new service won't need anything extra)
        BaseAgent.__init__(self, config_parser)
        role.init(config_parser)
        self.gen_string = config_parser.get('agent','STRING_TO_GENERATE')
        
        self.VAR_TMP = config_parser.get('agent','VAR_TMP')

        self.dir_file = join(self.VAR_TMP,'dir.pickle')
        self.mrc_file = join(self.VAR_TMP,'mrc.pickle')
        self.osd_file = join(self.VAR_TMP,'osd.pickle')
        self.mrc_lock = Lock()
        self.dir_lock = Lock()
        self.osd_lock = Lock()

        self.DIR = role.DIR
        self.MRC = role.MRC
        self.OSD = role.OSD
        
    def _create(self, post_params, class_file, pClass):
        if exists(class_file):
            return HttpErrorResponse(AgentException(
                AgentException.E_CONFIG_EXISTS).message)
        try:
            if type(post_params) != dict:
                raise TypeError()
            self.logger.debug('Creating class')
            p = pClass(**post_params)
            self.logger.debug('Created class')
        except (ValueError, TypeError) as e:
            ex = AgentException(AgentException.E_ARGS_INVALID, detail=str(e))
            self.logger.exception(e)
            return HttpErrorResponse(ex.message)
        except Exception as e:
            ex = AgentException(AgentException.E_UNKNOWN, detail=e)
            self.logger.exception(e)
            return HttpErrorResponse(ex.message)
        else:
            try:
                self.logger.debug('Openning file %s' % class_file)
                fd = open(class_file, 'w')
                pickle.dump(p, fd)
                fd.close()
            except Exception as e:
                ex = AgentException(AgentException.E_CONFIG_COMMIT_FAILED, 
                    detail=e)
                self.logger.exception(ex.message)
                return HttpErrorResponse(ex.message)
            else:
                self.logger.debug('Created class file')
                return HttpJsonResponse()

    def _stop(self, kwargs, class_file, pClass):
        self.logger.debug("_stop(kwargs=%s, class_file=%s, pClass=%s)" %
                (kwargs, class_file, pClass))

        if not exists(class_file):
            self.logger.error("class_file '%s' does not exist" % class_file)

            return HttpErrorResponse(AgentException(
                AgentException.E_CONFIG_NOT_EXIST).message)

        try:
            try:
                fd = open(class_file, 'r')
                p = pickle.load(fd)
                self.logger.debug('dump file %s loaded' %class_file)
                fd.close()
            except Exception as e:
                ex = AgentException(
                    AgentException.E_CONFIG_READ_FAILED, detail=e)
                self.logger.exception(ex.message)
                return HttpErrorResponse(ex.message)

            if 'drain' in kwargs:
                p.stop(kwargs['drain'])
            else:
                p.stop()

            self.logger.debug("Removing class_file '%s'" % class_file)
            remove(class_file)
            return HttpJsonResponse()

        except Exception as e:
            ex = AgentException(AgentException.E_UNKNOWN, detail=e)
            self.logger.exception(e)
            return HttpErrorResponse(ex.message)

    @expose('POST')
    def createDIR(self, kwargs):
        try:
            kwargs = self._DIR_get_params(kwargs)
        except AgentException as e:
            return HttpErrorResponse(e.message)
        with self.dir_lock:
            return self._create(kwargs, self.dir_file, self.DIR)

    @expose('POST')
    def createMRC(self, kwargs):
        try: 
            kwargs = self._MRC_get_params(kwargs)     
        except AgentException as e:
            return HttpErrorResponse(e.message)
        else:
            with self.mrc_lock:
                return self._create(kwargs, self.mrc_file, self.MRC)

    @expose('POST')
    def createOSD(self, kwargs):
        try:
            kwargs = self._OSD_get_params(kwargs)
        except AgentException as e:
            return HttpErrorResponse(e.message)
        else:
            with self.osd_lock:
                return self._create(kwargs, self.osd_file, self.OSD)

    @expose('POST')
    def stopDIR(self, kwargs):
        """Kill the DIR service"""
        with self.dir_lock:
            return self._stop(kwargs, self.dir_file, self.DIR)       

    @expose('POST')
    def stopMRC(self, kwargs):
        """Kill the MRC service"""
        with self.mrc_lock:
            return self._stop(kwargs, self.mrc_file, self.MRC)

    @expose('POST')
    def stopOSD(self, kwargs):
        """Kill the OSD service"""
        with self.osd_lock:
            return self._stop(kwargs, self.osd_file, self.OSD)       

    def _DIR_get_params(self, kwargs):
        ret = {}
        if 'uuid' not in kwargs:
            raise AgentException(
                AgentException.E_ARGS_MISSING, 'uuid')
        ret['uuid'] = kwargs.pop('uuid')
        return ret


    def _MRC_get_params(self, kwargs):
        ret = {}
        if 'dir_serviceHost' not in kwargs:
            raise AgentException(
                AgentException.E_ARGS_MISSING, 'dir service host')
        ret['dir_serviceHost'] = kwargs.pop('dir_serviceHost')
        if 'uuid' not in kwargs:
            raise AgentException(
                AgentException.E_ARGS_MISSING, 'uuid')
        ret['uuid'] = kwargs.pop('uuid')
        return ret
 
    def _OSD_get_params(self, kwargs):
        ret = {}
        if 'dir_serviceHost' not in kwargs:
            raise AgentException(
                AgentException.E_ARGS_MISSING, 'dir service host')
        ret['dir_serviceHost'] = kwargs.pop('dir_serviceHost')
        if 'uuid' not in kwargs:
            raise AgentException(
                AgentException.E_ARGS_MISSING, 'uuid')
        ret['uuid'] = kwargs.pop('uuid')
        ret['mkfs'] = kwargs['mkfs']
        return ret    

    @expose('POST')
    def startup(self, kwargs):
        self.state = 'RUNNING'
        self.logger.info('Agent started up')
        return HttpJsonResponse()

    @expose('POST')
    def set_snapshot(self, kwargs):
        if 'archive_url' not in kwargs:
            raise AgentException(
                AgentException.E_ARGS_MISSING, 'archive_url')

        self.logger.info('set_snapshot: restoring archive')

        archive_cmd = "wget --ca-certificate /etc/cpsagent/certs/ca_cert.pem "
        archive_cmd += kwargs['archive_url'] + " -O - | tar xz -C /"

        self.logger.debug('set_snapshot: %s' % archive_cmd)

        out, err = run_cmd(archive_cmd)

        self.logger.debug('set_snapshot: stdout %s' % out)
        self.logger.debug('set_snapshot: stderr %s' % err)

        self.logger.info('set_snapshot: archive restored successfully')
        return HttpJsonResponse()

    @expose('POST')
    def get_snapshot(self, kwargs):
        # pack data from:
        #     /etc/cpsagent/certs/ (original agent certificates)
        #     /etc/xos/xtreemfs/ (config files, SSL-certificates, policies)
        #     /var/lib/xtreemfs/ (save everything, after shutting down the services)
        #     /var/log/xtreemfs/ (xtreemfs log files)
        filename = "/root/snapshot.tar.gz"
        dirs = "var/lib/xtreemfs/ etc/xos/xtreemfs/ var/log/xtreemfs/ etc/cpsagent/certs"

        err, out = run_cmd("tar -czf %s %s" % (filename, dirs), "/")
        if err:
            self.logger.exception(err)
            return HttpErrorResponse(err)

        return HttpFileDownloadResponse("snapshot.tar.gz", filename)
        
    @expose('POST')
    def set_certificates(self, kwargs):
        self.logger.debug('set_snapshot called')
    	# write certificates and truststore to the xtreemfs config directory
    	path = "/etc/xos/xtreemfs/truststore/certs"
    	if not exists(path):
  			makedirs(path)
    	open(path + "/dir.p12", 'wb').write(base64.b64decode(kwargs['dir']))
    	open(path + "/mrc.p12", 'wb').write(base64.b64decode(kwargs['mrc']))
    	open(path + "/osd.p12", 'wb').write(base64.b64decode(kwargs['osd']))
    	open(path + "/trusted.jks", 'wb').write(base64.b64decode(kwargs['truststore']))
    	return HttpJsonResponse()
