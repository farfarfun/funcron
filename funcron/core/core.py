
import argparse
import subprocess
from time import sleep

from notebuild.shell import run_shell, run_shell_list
from notecron.tasks import start
from notetool.tool.log import log

logger = log("notebuild")


class JobScheduler:
    def __init__(self):
        pass

    def start(self):
        logger.info("start")
        subprocess.check_output(
            'nohup notecron _start >>/notechats/logs/jobs/notecron-run-$(date +%Y-%m-%d).log 2>&1 &', shell=True)

    def _start(self):
        logger.info("start")
        start()

    def stop(self):
        logger.info("stop")

        port = subprocess.check_output("ps x | grep notecron", shell=True)

        for line in port.decode().strip('\n').split('\n'):
            a = [i for i in line.split(' ') if len(i) > 0]

            if 'notecron' in a[-2] and a[-1] in ('restart', 'start', '_start'):
                subprocess.check_output('kill -9 {}'.format(a[0]), shell=True)
                logger.info("kill zhe process \n{}\n".format(line))

    def restart(self):
        self.stop()
        sleep(3)
        self.start()


def command_line_parser():
    parser = argparse.ArgumentParser(description="Test")
    parser.add_argument('command')
    args = parser.parse_args()
    return args


def notecron():
    args = command_line_parser()
    job = JobScheduler()
    if args.command == 'run':
        job.start()
    elif args.command == '_start':
        job._start()
    elif args.command == 'start':
        job.start()
    elif args.command == 'stop':
        job.stop()
    elif args.command == 'restart':
        job.restart()
    else:
        logger.info("unknown")
