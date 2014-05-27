from threading import Thread

from conpaas.core.expose import expose
from conpaas.core.manager import BaseManager

from conpaas.core.https.server import HttpJsonResponse, HttpErrorResponse

from conpaas.services.helloworld.agent import client

class ContextManager(Object):

    # Manager states - Used by the Director
    S_INIT = 'INIT'         # manager initialized but not yet started
    S_INITCTX = 'INIT_CTX'         # manager initialized but not yet started
    S_PROLOGUE = 'PROLOGUE' # manager is starting up
    S_RUNNING = 'RUNNING'   # manager is running
    S_ADAPTING = 'ADAPTING' # manager is in a transient state - frontend will keep
                            # polling until manager out of transient state
    S_EPILOGUE = 'EPILOGUE' # manager is shutting down
    S_STOPPED = 'STOPPED'   # manager stopped
    S_ERROR = 'ERROR'       # manager is in error state

    def __init__(self, config_parser, **kwargs):
        #BaseManager.__init__(self, config_parser)
        self.nodes = []
        # Setup the clouds' controller
        self.state = self.S_INIT_CTX

    def _do_startup(self, cloud):
        startCloud = self._init_cloud(cloud)

        #self.controller.add_context_replacement(dict(STRING='helloworld'))

    @expose('POST')
    def shutdown(self, kwargs):
        self.state = self.S_EPILOGUE
        Thread(target=self._do_shutdown, args=[]).start()
        return HttpJsonResponse()

    def _do_shutdown(self):
        self.state = self.S_STOPPED
        return HttpJsonResponse()

    @expose('GET')
    def get_machine_info(self, kwargs):
        if len(kwargs) != 0:
            return HttpErrorResponse('ERROR: Arguments unexpected')

        return HttpJsonResponse({'state': self.state, 'type': 'init_ctx'})


    @expose('GET')
    def get_helloworld(self, kwargs):
        if self.state != self.S_RUNNING:
            return HttpErrorResponse('ERROR: Wrong state to get_helloworld')

        messages = []

        return HttpJsonResponse({ 'helloworld': "Hello from ContextManager" })
