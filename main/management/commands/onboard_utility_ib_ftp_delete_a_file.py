from django.core.management.base import NoArgsCommand
from main import constants
from main import abstract
import pandas as pd
import os
import pdb

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        '''
        deletes a file in the FTP_DIR directory at the IB_FTP site.
        '''

        from onboarding.interactive_brokers import onboarding as onboard
        from ftplib import FTP

        ftp = FTP(onboard.IB_FTP)
        ftp.login(user=onboard.FTP_USERNAME, passwd=onboard.FTP_PASSWORD)
        ftp.cwd(onboard.FTP_DIR)
        
        data_before = []
        ftp.dir(data_before.append)

        files=[]
        file_tail = '.zip.gpg'
        for i in range(len(data_before)):
            files = files + [elem for elem in data_before[i].split(' ') if len(elem) > len(file_tail) and elem[-len(file_tail):] == file_tail]
        print('files before delete:', files)

        f = ''
        print('deleting:', f)
        try:
            ftp.delete(f)
        except:
            print('delete failed')

        data_after = []
        ftp.dir(data_after.append)
        files=[]
        file_tail = '.zip.gpg'
        for i in range(len(data_after)):
            files = files + [elem for elem in data_after[i].split(' ') if len(elem) > len(file_tail) and elem[-len(file_tail):] == file_tail]
        print('files after delete:', files)

        
