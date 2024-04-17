from django.core.management.base import BaseCommand
from django.core.mail import send_mail, EmailMultiAlternatives
import requests
from vessel_assignment_checker.models import *
import datetime
import pytz

EMAIL_FORMAT_TXT_FILE = 'C:/Users/gcanuto/Documents/NominationProject/web/email.txt'

COMPANY_NAME = "Saam Towage"
COMPETITORS = ["Seaspan", "Group Ocean", "Samson"] # Make sure those are spelled correctly

PEOPLE_TO_RECEIVE_ALERT = ['gcanuto@saamtowage.com', 'igabriel@saamtowage.com', 'dispatch.yvr@saamtowage.com', 'danielle.fagundes@saamtowage.com', 'tpow@saamtowage.com', 'cyilmaz@saamtowage.com']
#PEOPLE_TO_RECEIVE_ALERT = ['gcanuto@saamtowage.com']

# We do not operate the ships that come into Cargil, Delta Port and Robert Banks, so we will ignore those.
NOT_TERMINALS = ['CG1', 'CG2', 'RB1', 'RB2', 'DP1', 'DP2', 'DP3', 'PET']

# Setting a variable to collect the time
tz = pytz.timezone('America/Vancouver')
time_now = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# Log file location
LOG_FILE = 'C:/Users/gcanuto/Documents/NominationProject/web/log_orders.txt'

def trim_log_file(max_lines=100, delete_lines=50):
    with open(LOG_FILE, 'r') as file:
        lines = file.readlines()

    # Check if the log has exceeded the maximum number of lines
    if len(lines) > max_lines:
        # Trim the log by deleting the first delete_lines
        lines = lines[delete_lines:]

        # Write the trimmed log back to the file
        with open(LOG_FILE, 'w') as file:
            file.writelines(lines)
    

def get_log_orders():
    # Get the last job ids:
    log_executions = None
    with open(LOG_FILE, 'r') as log_file:
        log_executions = log_file.read()

    log_executions = log_executions.split('\n')
    last_orders = []

    for execution in log_executions:
        split =  execution.split(',')
        if len(split) > 1:
            time, id = split
            if id != 'noVessels':
                last_orders.append(int(id))


    return last_orders

def minutes_from_noon():
    '''
    This function returns how many minutes has passed from Noon at that day
    '''
    now = datetime.datetime.now(tz)
    # Convert the date object to a datetime object by combining it with a specific time
    datetime_noon = datetime.datetime.combine(now, datetime.time(hour=12, minute=0))  # Setting the time to 9:30 AM
    datetime_noon = tz.localize(datetime_noon)
    minutes_dif = (now - datetime_noon).total_seconds() / 60

    return minutes_dif
    

def send_email_vessel_left(vessel_name):
    '''
    Function that sends the email notifying of the vessel departure.
    '''
    now = datetime.datetime.now(tz)
    subject, from_email, to = f'Vessel {vessel_name} Departed.', 'gcanuto.job@gmail.com', ['gcanuto@saamtowage.com', 'cyilmaz@saamtowage.com']
    text_content = f'Hi! \n As of last scan on {time_now}, the {vessel_name} left, and is ready to be invoiced.'
    html_content =f'<div>Hi!<br>As of last scan on {time_now}, the {vessel_name} left, and is ready to be invoiced.</div>'
    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()

class Command(BaseCommand):
    help = 'Sends an email with Saam Towage\'s  vessels that were not assigned correctly.'

    trim_log_file() # Cleans a little bit of the logs if its getting to big.

    def handle(self, *args, **kwargs):
        tz = pytz.timezone('America/Vancouver')
        now = datetime.datetime.now(tz)
        try:
            response = requests.get('https://ppaportal.portlink.co/api/pdams/GetCurrentVesselTraffic')
            response.raise_for_status()
            
            data = response.json()["data"]
            entitled_vessels = [vessel.serialize()["name"] for vessel in Vessel.objects.all()]

            mis_assigned_vessels = []

            orders_previously_notifieds = get_log_orders()

            for job in data:
                vessel_name = job["vessel"]["name"]
                tug_from = job["fromTugLaunchName"]
                tug_to = job["toTugLaunchName"]
                from_location = job["fromLocationShortCode"]
                to_location = job["toLocationShortCode"]
                job_id = int(job["jobId"])

                # Clean database up (delete vessels dispatched away from Vancouver)
                if vessel_name in entitled_vessels and job["status"] == "Dispatched" and job["toLocationShortCode"] == "BRO" and (tug_from not in COMPETITORS and tug_to not in COMPETITORS):
                    Vessel.objects.filter(name=vessel_name).delete()
                    send_email_vessel_left(vessel_name)
                    try:
                        entitled_vessels.remove(vessel_name)
                        
                    except ValueError:
                        pass
                    continue
                #if vessel_name in entitled_vessels and (tug_from in COMPETITORS or tug_to in COMPETITORS):
                # Now, if the vessel is coming to a terminal which we do not operate, it won't send the email.
                # If we have already notified about the vessel, it won't notify again.
                if vessel_name in entitled_vessels and ( (tug_from in COMPETITORS and from_location not in NOT_TERMINALS) or (tug_to in COMPETITORS and to_location not in NOT_TERMINALS) ) and (job_id not in orders_previously_notifieds):
                    mis_assigned_vessels.append({
                        "status":job["status"],
                        "time":datetime.datetime.fromisoformat(job["orderTime"].replace("Z", "+00:00")),
                        "name":vessel_name.title(),
                        "etd":datetime.datetime.fromisoformat(job["etd"].replace("Z", "+00:00")),
                        "from":job["fromLocationShortCode"],
                        "to":job["toLocationShortCode"],
                        "agency":job["agencyName"],
                        "tug_from":tug_from,
                        "tug_to":tug_to,
                        "job_id": job_id
                        })
                
            if kwargs["print"]:
                print(mis_assigned_vessels)
            else:
                vessels_string = ""
                for i, item in enumerate(mis_assigned_vessels):
                    vessels_string = vessels_string + f", {item['name']}" if i != 0 else item['name']
                subject, from_email, to = f' PPA JOB MISASSIGNMENT(?) - ACTION REQUIRED', 'gcanuto.job@gmail.com', PEOPLE_TO_RECEIVE_ALERT

                text_content = f'Dear Team\n As of last scan on {time_now}, it appears that there may be {len(mis_assigned_vessels)} vessel(s) wrongly assigned on PPA. Please take immediate action following the steps outlined below:'

                html_content =f'<div>Hi!<br>As of last scan on {time_now}, there are {len(mis_assigned_vessels)} vessel(s) that have been wrongfully assigned.</div>'
                html_content = f'<div>Dear Team<br> As of last scan on {time_now}, it appears that there <strong style="background-color: yellow;"> may be {len(mis_assigned_vessels)} vessel(s) wrongly assigned on PPA </strong>. Please take immediate action following the steps outlined below:</div>'
                if len(mis_assigned_vessels) > 0:
                    text_content += ' The vessels are:\n\n{vessels_string}.'
                    html_content += '<h2>The vessels are:</h2><table style="font-family: arial, sans-serif; border-collapse: collapse; width: 100%;"><tr><th>Status</th><th>Order Time</th><th>Vessel Name</th><th>ETD</th><th>From</th><th>To</th><th>Agency</th><th>Tug From</th><th>Tug To</th></tr>'
                    
                    f = open(LOG_FILE, 'a')
                    for vessel in mis_assigned_vessels:
                        html_content += f'''<tr>
                            <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">{vessel["status"]}</td>
                            <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">{vessel["time"].strftime("%Y-%m-%d %H:%M:%S")}</td>
                            <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">{vessel["name"]}</td>
                            <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">{vessel["etd"].strftime("%Y-%m-%d %H:%M:%S")}</td>
                            <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">{vessel["from"]}</td>
                            <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">{vessel["to"]}</td>
                            <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">{vessel["agency"]}</td>
                            <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">{vessel["tug_from"]}</td>
                            <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">{vessel["tug_to"]}</td>
                        </tr>'''
                        message = time_now + ',' + str(vessel["job_id"])
                        print(vessel["name"])
                        f.write(f"{message}\n")

                    f.close()

                    html_content += '</table>'

                    with open(EMAIL_FORMAT_TXT_FILE, 'r') as file:
                        # Read the contents of the file
                        file_contents = file.read()

                    html_content += file_contents

                else:
                    '''
                    If there are no mis-assigned vessel, save it to log
                    Every monday at noon it sends an email to gcanuto@saamtowage.com
                    '''
                    text_content += 'Everything looks good!'
                    html_content += '<h2>Everything looks good!</h2>'
                    to = ['gcanuto@saamtowage.com', 'cyilmaz@saamtowage.com']

                    with open(LOG_FILE, 'a') as log_file:
                        log_file.write(f"{time_now},noVessels\n")

                
                minutes_diff = minutes_from_noon() # It returns how past Noon we are in minutes

                if (len(mis_assigned_vessels) > 0) or ((minutes_diff > 0) and (minutes_diff < 20)):
                    '''
                    If there were no miss assigned vessels, and it is close by the Noon, it sends gcanuto an email to assure the software is working
                    If there was an miss assigned vessel, it notifies everybody
                    '''
                    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
                    msg.attach_alternative(html_content, "text/html")
                    msg.send()
                


        except requests.HTTPError as err:
            if response.status_code == 404:
                print("The resource was not found!")
            else:
                print(f"An error occurred: {err}")
            with open("scan-error-logs.txt", "a") as log_file:
                log_file.write(f"{time_now}: {err}")

    def add_arguments(self, parser):
        parser.add_argument(
            '--print',
            action='store_true',
            help='Include to skip emailing the list and to just print it out.',
        )
