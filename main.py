import time
import logging
from lcu_driver.connection import Connection
import threading
from utils import MyConnector
import argparse

logger = logging.getLogger("lol-autolockin")
connector = MyConnector()


def start():
    t = threading.Thread(target=connector.start)
    t.start()


@connector.ready
async def connect(connection: Connection):
    logger.info("Connected to LCU API")
    in_champion_select = False
    position = -1
    queue = -2
    summ_request = await connection.request("get", "/lol-login/v1/session")
    summ_info = await summ_request.json()
    logger.debug(summ_info)
    acc_id = summ_info["summonerId"]
    logger.info("Summoner id is " + str(acc_id))
    while True:
        ch_select = await connection.request("get", "/lol-champ-select/v1/session")
        ch_select_info = await ch_select.json()
        logger.debug(ch_select_info)
        if "errorCode" in ch_select_info and in_champion_select:
            logger.info("No longer in champion select")
            position = -1
            queue = -2
            in_champion_select = False
        if "errorCode" not in ch_select_info and not in_champion_select:
            logger.info("Entered champion select")
            in_champion_select = True
        if in_champion_select:
            queue_request = await connection.request("get", "/lol-gameflow/v1/session")
            queue_info = await queue_request.json()
            logger.debug(queue_info)
            new_queue = queue_info["gameData"]["queue"]["id"]
            if new_queue != queue:
                logger.info("Different queue detected. Queue ID: " + str(new_queue))
                queue = new_queue
            if queue in [400, 420, 440]:
                for user in ch_select_info["myTeam"]:
                    if user["summonerId"] == acc_id:
                        if position == -1:
                            logger.info("User position is " + str(user["cellId"]))
                        position = user["cellId"]
                for event_group in ch_select_info["actions"]:
                    for event in event_group:
                        if event["actorCellId"] == position and event["type"] == "pick" and event["isInProgress"]:
                            event_id = event["id"]
                            timer = await connection.request("get", "/lol-champ-select/v1/session/timer")
                            timer_info = await timer.json()
                            logger.debug(timer_info)
                            current = time.time()
                            if "internalNowInEpochMs" in timer_info:
                                remaining = (timer_info["internalNowInEpochMs"] + timer_info[
                                    "adjustedTimeLeftInPhase"]) / 1000 - current
                                logger.info("Detected pick turn. Sleeping " + str(remaining - 1))
                                time.sleep(remaining - 1)
                                lock_in = await connection.request("post", "/lol-champ-select/v1/session/actions/" +
                                                                   str(event_id) + "/complete")
                                lock_in_info = await lock_in.json()
                                logger.debug(lock_in_info)
                                logger.info("Locked in.")
        
        time.sleep(5)


@connector.close
async def disconnect(_):
    logger.info("Disconnected from League, exiting...")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", help="Enable debug log", action="store_true")
    args = parser.parse_args()
    logger.setLevel("DEBUG")
    with open("logfile.log", "a+") as file:
        file.write("\n\n\n\n" + str(time.asctime()) + "\n")
    if args.debug:
        logging.basicConfig(filename='logfile.log', level=logging.DEBUG)
    else:
        logging.basicConfig(filename='logfile.log', level=logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    logger.info("Waiting for League of Legends...")
    start()


if __name__ == "__main__":
    main()
