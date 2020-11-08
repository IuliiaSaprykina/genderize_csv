from genderize import Genderize, GenderizeException
import csv
import sys
import os.path
import time
import argparse
import logging
import tempfile
from csv import DictReader, DictWriter

import jpyhelper as jpyh


def genderize(args):
    print(args)

    #File initialization
    dir_path = os.path.dirname(os.path.realpath(__file__))

    logging.basicConfig(filename=dir_path + os.sep + "log.txt", level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(name)s %(message)s')
    logger=logging.getLogger(__name__)

    ofilename, ofile_extension = os.path.splitext(args.output)

    ofile = ofilename + "_" + time.strftime("%Y%m%d-%H%M%S") + ".csv"
    ifile = args.input

    if os.path.isabs(ifile):
        print("\n--- Input file: " + ifile)
    else:
        print("\n--- Input file: " + dir_path + os.sep + ifile)

    if os.path.isabs(ofile):
        print("--- Output file: " + ofile)
    else:
        print("--- Output file: " + dir_path + os.sep + ofile + "\n")

    #File integrity checking
    if not os.path.exists(ifile):
        print("--- Input file does not exist. Exiting.\n")
        sys.exit()

    if not os.path.exists(os.path.dirname(ofile)):
        print("--- Error! Invalid output file path. Exiting.\n")
        sys.exit()

    #Some set up stuff
    csv.field_size_limit(sys.maxsize)

    #Initialize API key
    if not args.key == "NO_API":
        print("--- API key: " + args.key + "\n")
        genderize = Genderize(
            user_agent='GenderizeDocs/0.0',
            api_key='169f6a8e933dcec15a57235d7fde49d6')
        key_present = True
    else:
        print("--- No API key provided.\n")
        key_present = False

    #Open ifile
    with open(ifile, 'r', encoding="utf8") as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',',  quotechar='"', skipinitialspace=True)
        line_count = 0
        first_name = []
        users_id = []
        input_fields = []
        rows = []
        input_fields = next(readCSV)
        for row in readCSV: #Read CSV into first_name list
            rows.append(row)
            line_count += 1

        if len(input_fields) > 1:
            for row in rows:
                first_name.append(row[1])
                users_id.append(row[0])
        else:
            for row in rows:
                first_name.append(row[0])

        if args.noheader == False and first_name[0] in input_fields:
            first_name.pop(0) #Remove header

        o_first_name = list()
        for l in first_name:
            for b in l:
                o_first_name.append(b)

        if args.auto == True:
            # uniq_first_name = list(set(o_first_name))
            chunks = list(jpyh.splitlist(first_name, 10));
            print("--- Read CSV with " + str(len(first_name)) + " first_name. " + str(len(first_name)) + " unique.")
        else:
            chunks = list(jpyh.splitlist(first_name, 10));
            print("--- Read CSV with " + str(len(first_name)) + " first_name")

        print("--- Processed into " + str(len(chunks)) + " chunks")

        if jpyh.query_yes_no("\n---! Ready to send to Genderdize. Proceed?") == False:
            print("Exiting...\n")
            sys.exit()

        if os.path.isfile(ofile):
            if jpyh.query_yes_no("---! Output file exists, overwrite?") == False:
                print("Exiting...\n")
                sys.exit()
            print("\n")

        if args.auto == True:
            ofile = ofile + ".tmp"
          
        response_time = []
        gender_responses = list()
        output_fields = [*input_fields, "gender", "probability", "count"]
        if args.override == False:
            with open(ofile, 'w', newline='', encoding="utf8") as f:
                writer = csv.writer(f)
                writer.writerow(output_fields)
                chunks_len = len(chunks)
                stopped = False
                for index, chunk in enumerate(chunks):
                    if stopped:
                        break
                    success = False
                    while not success:
                        try:
                            start = time.time()

                            if key_present:
                                dataset = genderize.get(chunk)
                                
                            else:
                                dataset = Genderize(
                                    user_agent='GenderizeDocs/0.0',
                                    api_key='169f6a8e933dcec15a57235d7fde49d6').get(chunk)
                                
                            gender_responses.append(dataset)
                            success = True
                        except GenderizeException as e:
                            print("\n" + str(e))
                            logger.error(e)

                            #Error handling
                            if "response not in JSON format" in str(e) and args.catch == True:
                                if jpyh.query_yes_no("\n---!! 502 detected, try again?") == True:
                                    success = False
                                    continue
                            elif "Invalid API key" in str(e) and args.catch == True:
                                print("\n---!! Error, invalid API key! Check log file for details.\n")
                            else:
                                print("\n---!! GenderizeException - You probably exceeded the request limit, please add or purchase a API key. Check log file for details.\n")
                            stopped = True
                            break

                        response_time.append(time.time() - start)
                        print("Processed chunk " + str(index + 1) + " of " + str(chunks_len) + " -- Time remaining (est.): " + \
                            str( round( (sum(response_time) / len(response_time) * (chunks_len - index - 1)), 3)) + "s")

                        break
                j = 0
                response_arr = list()
                for data in gender_responses:
                    for el in data:
                        response_arr.append(el)
                
                for row in rows:
                    row.append(response_arr[j]['gender'])
                    row.append(response_arr[j]['probability'])
                    row.append(response_arr[j]['count'])
                    j += 1
                
                for row in rows:
                    writer.writerow(row)


        if args.auto == True:
            print("\nCompleting identical first_name...\n")
            #AUTOCOMPLETE first_namey

            #Create master dict
            gender_dict = dict()
            for response in gender_responses:
                for d in response:
                    gender_dict[d.get("name")] = [d.get("count"), d.get("gender"), d.get("probability")]
                
                
            filename, file_extension = os.path.splitext(ofile)
            with open(filename, 'w', newline='', encoding="utf8") as f:
                writer = csv.writer(f, delimiter='-')
                writer.writerow(list(["name", "count", "gender", "probability"]))

                for name in o_first_name:
                    data = gender_dict.get(name)
                    writer.writerow([name, data[1], data[1], data[2]])
            
        if args.override == True:
            output_fields = [*input_fields]
            with open(ofile, 'w', newline='', encoding="utf8") as f:
                writer = csv.writer(f)
                writer.writerow(output_fields)
                chunks_len = len(chunks)
                stopped = False
                for index, chunk in enumerate(chunks):
                    if stopped:
                        break
                    success = False
                    while not success:
                        try:
                            start = time.time()

                            if key_present:
                                dataset = genderize.get(chunk)
                            else:
                                dataset = Genderize(
                                    user_agent='GenderizeDocs/0.0',
                                    api_key='169f6a8e933dcec15a57235d7fde49d6').get(chunk)

                            gender_responses.append(dataset)
                            success = True
                        except GenderizeException as e:
                            print("\n" + str(e))
                            logger.error(e)

                            #Error handling
                            if "response not in JSON format" in str(e) and args.catch == True:
                                if jpyh.query_yes_no("\n---!! 502 detected, try again?") == True:
                                    success = False
                                    continue
                            elif "Invalid API key" in str(e) and args.catch == True:
                                print("\n---!! Error, invalid API key! Check log file for details.\n")
                            else:
                                print("\n---!! GenderizeException - You probably exceeded the request limit, please add or purchase a API key. Check log file for details.\n")
                            stopped = True
                            break

                        response_time.append(time.time() - start)
                        print("Processed chunk " + str(index + 1) + " of " + str(chunks_len) + " -- Time remaining (est.): " + \
                            str( round( (sum(response_time) / len(response_time) * (chunks_len - index - 1)), 3)) + "s")
            
                        break
                
                i = 0
                response_arr = list()
                for data in gender_responses:
                    for el in data:
                        response_arr.append(el)
                

                index = len(rows)
                for row in rows:
                    # print(rows[-1][-2])
                    if response_arr[i]['gender'] == 'male':
                        rows[i][-1] = "1"
                        rows[i][-2] = "0"
                    else :
                        rows[i][-1] = "0"
                        rows[i][-2] = "1"
                    i += 1
                
                for row in rows:
                    writer.writerow(row)
            print("Done!\n")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Bulk genderize.io script')
    required = parser.add_argument_group('required arguments')

    required.add_argument('-i','--input', help='Input file name', required=True)
    required.add_argument('-o','--output', help='Output file name', required=True)
    parser.add_argument('-k','--key', help='API key', required=False, default="NO_API")
    parser.add_argument('-c','--catch', help='Try to handle errors gracefully', required=False, action='store_true', default=True)
    parser.add_argument('-a','--auto', help='Automatically complete gender for identical first_name', required=False, action='store_true', default=False)
    parser.add_argument('-nh','--noheader', help='Input has no header row', required=False, action='store_true', default=False)
    parser.add_argument('-OVR','--override', help='Override default column output. ', required=False, action='store_true', default=False)

    genderize(parser.parse_args())
