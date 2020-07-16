import logging
import time

from lcu_driver import Connector
from lcu_driver.utils import return_process


def wait_for_league():
    process = None
    while not process:
        process = return_process(['LeagueClientUx.exe', 'LeagueClientUx'])
        time.sleep(2)
    return process


logger = logging.getLogger("rogama-utils")


class MyConnector(Connector):
    def start(self) -> None:
        """Starts the connector. This method should be overridden if different behavior is required.
    
        :rtype: None
        """
        try:
            def wrapper():
                connection = wait_for_league()
                self.create_connection(connection)
                self.loop.run_until_complete(self.connection.init())
                
                if self._repeat_flag and len(self.ws.registered_uris) > 0:
                    logger.debug('Repeat flag=True. Looking for new clients.')
                    wrapper()
            
            wrapper()
        except KeyboardInterrupt:
            logger.info('Event loop interrupted by keyboard')
