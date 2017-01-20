#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
required packages to install
linux: apt-get install tesseract
python3: pip-install pyPdf2
"""
import argparse
# from PyPDF2 import PdfFileReader
import os
import shutil
import sys
import json
import subprocess
import logging
import random
import string


logger = logging.getLogger('pdf_parsers.social_security')


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def get_pdf_content_lines(pdf_file_path):
    with open(pdf_file_path, 'rb') as f:
        tmp_file_id = id_generator()
        subprocess.run(['pdftotext', pdf_file_path, '/tmp/' + tmp_file_id], stdout=subprocess.PIPE)
        with open('/tmp/' + tmp_file_id, 'rb') as f:
            return f.read()


# for each item to extract its string, the value is found between
# the pairs in the list e.g. SSN is found between "SSN:", "SPOUSE SSN:"
keywords = {
    'RetirementAtFull': ['Your payment would be about\n', '\nat full retirement age'],
    'BenefitsColumn': ['Social Security three months before your 65th birthday to enroll in Medicare.\n\n', '\n\n* Your estimated benefits are based on current law.'],
    'EstimatedTaxableEarnings': ['\n\t\n', '\nYour Social Security number (only the last four digits are shown to help prevent identity theft)'],
    'LastYear': ['You paid:', ''],
    'PaidColumn': ['You paid:\t\nYour employers paid:\t\n\n', '\n\nNote: Currently, you and your employer each pay'],
    'PaidThisYear': ['', ''],
    'EmployerPaidThisYear': ['', ''],
    'PaidLastYear': ['', ''],
    'EmployerPaidLastYear': ['', ''],
}

output = {
    "sections": [
        {
            "name": "Estimated Benefits",
            "fields": {
                "RetirementAtFull": "",
                'BenefitsColumn': '',
                'RetirementAtAge70': '',
                'RetirementAtAge62': '',
                'SurvivorsChild': '',
                'SurvivorsSpouseWithChild': '',
                'SurvivorsSpouseAtFull': '',
                'SurvivorsSpouseAtFull': '',
                'SurvivorsTotalFamilyBenefitsLimit': '',
                'EstimatedTaxableEarnings': '',
            }
        },
        {
            'name': 'Estimated Earnings',
            'fields': {
                'LastYear': '',
            }
        },
        {
            'name': 'Estimated Paid',
            'fields': {
                'PaidColumn': '',
                'PaidThisYearSocialSecurity': '',
                'EmployerPaidThisYearSocialSecurity': '',
                'PaidThisYearMedicare': '',
                'EmployerPaidThisYearMedicare': '',
            }
        },
    ]
}


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


def parse_item(key, s):
    sub_str = keywords[key]
    start = sub_str[0]
    end = sub_str[1]
    result = find_between(s, start, end)
    logger.error(sub_str)
    logger.error(start)
    logger.error(end)
    logger.error(result)

    return result.lstrip().rstrip().lstrip('.').rstrip('.').rstrip('\n')


def parse_text(string):
    i = 0
    for section in output["sections"]:
        for k, v in list(section["fields"].items()):
            if k in list(keywords.keys()):
                res = parse_item(k, string)
                if k == 'BenefitsColumn':
                    benefits = res.split('\n')
                    if len(benefits) > 1:
                        output['sections'][i]['fields']['RetirementAtAge70'] = '$' + benefits[1]
                        output['sections'][i]['fields']['RetirementAtAge62'] = '$' + benefits[2]
                        output['sections'][i]['fields']['Disability'] = '$' + benefits[3]
                        output['sections'][i]['fields']['SurvivorsChild'] = '$' + benefits[4]
                        output['sections'][i]['fields']['SurvivorsSpouseWithChild'] = '$' + benefits[5]
                        output['sections'][i]['fields']['SurvivorsSpouseAtFull'] = '$' + benefits[6]
                        output['sections'][i]['fields']['SurvivorsSpouseAtFull'] = '$' + benefits[7]
                        output['sections'][i]['fields']['SurvivorsTotalFamilyBenefitsLimit'] = '$' + benefits[8]
                elif k == 'PaidColumn':
                    paid = res.split('\n')
                    if len(paid) > 1:
                        output['sections'][i]['fields']['PaidThisYearSocialSecurity'] = paid[4]
                        output['sections'][i]['fields']['EmployerPaidThisYearSocialSecurity'] = paid[5]
                        output['sections'][i]['fields']['PaidThisYearMedicare'] = paid[7]
                        output['sections'][i]['fields']['EmployerPaidThisYearMedicare'] = paid[8]
                
                if output["sections"][i]["fields"][k] == "":
                    output["sections"][i]["fields"][k] = res

        i += 1
    return output


def parse_vector_pdf(fl):
    logger.error(get_pdf_content_lines(fl))
    res = get_pdf_content_lines(fl).decode("utf-8")
    return parse_text(res)


def parse_scanned_pdf(fl):
    tmp_pdfs = "tmp"
    if not os.path.exists(tmp_pdfs):
        os.makedirs(tmp_pdfs)

    os.system("convert -density 300 -alpha Off {0} {1}/img.tiff".format(fl, tmp_pdfs))
    os.system("tesseract {0}/img.tiff {0}/out".format(tmp_pdfs))
    cmd = "touch {0}/out.txt && sed -i -e 's/—/-/g' {0}/out.txt".format(tmp_pdfs)
    os.system(cmd)
    with open("{0}/out.txt".format(tmp_pdfs), 'r') as f:
        txt = f.read()

    shutil.rmtree(tmp_pdfs)
    txt = ''.join(txt)
    return parse_text(txt)


def clean_results(results):
    clean_output = {}
    clean_output['RetirementAtFull'] = results['sections'][0]['fields']['RetirementAtFull']
    clean_output['RetirementAtAge70'] = results['sections'][0]['fields']['RetirementAtAge70']
    clean_output['RetirementAtAge62'] = results['sections'][0]['fields']['RetirementAtAge62']
    clean_output['SurvivorsChild'] = results['sections'][0]['fields']['SurvivorsChild']
    clean_output['SurvivorsSpouseWithChild'] = results['sections'][0]['fields']['SurvivorsSpouseWithChild']
    clean_output['SurvivorsSpouseAtFull'] = results['sections'][0]['fields']['SurvivorsSpouseAtFull']
    clean_output['SurvivorsSpouseAtFull'] = results['sections'][0]['fields']['SurvivorsSpouseAtFull']
    clean_output['SurvivorsTotalFamilyBenefitsLimit'] = results['sections'][0]['fields']['SurvivorsTotalFamilyBenefitsLimit']
    clean_output['EstimatedTaxableEarnings'] = results['sections'][0]['fields']['EstimatedTaxableEarnings']
    clean_output['LastYear'] = results['sections'][1]['fields']['LastYear']
    clean_output['PaidThisYearSocialSecurity'] = results['sections'][2]['fields']['PaidThisYearSocialSecurity']
    clean_output['EmployerPaidThisYearSocialSecurity'] = results['sections'][2]['fields']['EmployerPaidThisYearSocialSecurity']
    clean_output['PaidThisYearMedicare'] = results['sections'][2]['fields']['PaidThisYearMedicare']
    clean_output['EmployerPaidThisYearMedicare'] = results['sections'][2]['fields']['EmployerPaidThisYearMedicare']

    return clean_output


def parse_pdf(filename):
    try:
        # check if pdf is searchable, pdffonts lists fonts used in pdf, if scanned (image), list is empty
        cmd_out = subprocess.getstatusoutput("pdffonts {} | wc -l".format(filename))
        if int(cmd_out[1]) > 2:
            result = parse_vector_pdf(filename)
        else:
            result = parse_scanned_pdf(filename)

        logger.info('Social Security PDF parsed OK')
        return clean_results(result)
    except Exception as e:
        logger.error(e)
        return


def main():
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('-f', '--file', type=str, help='Input pdf file', required=True)

        args = parser.parse_args()

        # check if pdf is searchable, pdffonts lists fonts used in pdf, if scanned (image), list is empty
        cmd_out = subprocess.getstatusoutput("pdffonts {} | wc -l".format(args.file))
        if int(cmd_out[1]) > 2:
            result = parse_vector_pdf(args.file)
        else:
            result = parse_scanned_pdf(args.file)

        print(json.dumps(clean_results(result), sort_keys=True, indent=4, separators=(',', ': ')))
        return result
    except KeyboardInterrupt:
        print('Keyboard interrupt!')
        return 0
    except Exception as e:
        print(e)
        raise e


if __name__ == "__main__":
    sys.exit(main())
