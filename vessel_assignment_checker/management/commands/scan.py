from django.core.management.base import BaseCommand
from django.core.mail import send_mail, EmailMultiAlternatives
import requests
from vessel_assignment_checker.models import *
import datetime
import pytz

COMPANY_NAME = "Saam Towage"
COMPETITORS = ["Seaspan", "Group Ocean", "Samson"] # Make sure those are spelled correctly

class Command(BaseCommand):
    help = 'Sends an email with Saam Towage\'s  vessels that were not assigned correctly.'

    def handle(self, *args, **kwargs):
        tz = pytz.timezone('America/Vancouver')
        try:
            response = requests.get('https://ppaportal.portlink.co/api/pdams/GetCurrentVesselTraffic')
            response.raise_for_status()
            
            data = response.json()["data"]
            entitled_vessels = [vessel.serialize()["name"] for vessel in Vessel.objects.all()]

            mis_assigned_vessels = []

            for job in data:
                vessel_name = job["vessel"]["name"]
                tug_from = job["fromTugLaunchName"]
                tug_to = job["toTugLaunchName"]
                # Clean database up (delete vessels dispatched away from Vancouver)
                if job["status"] == "Dispatched" and job["toLocationShortCode"] == "BRO" and (tug_from not in COMPETITORS and tug_to not in COMPETITORS):
                    Vessel.objects.filter(name=vessel_name).delete()
                    try:
                        entitled_vessels.remove(vessel_name)
                    except ValueError:
                        pass
                    continue
                if vessel_name in entitled_vessels and (tug_from in COMPETITORS or tug_to in COMPETITORS):
                    mis_assigned_vessels.append({
                        "status":job["status"],
                        "time":datetime.datetime.fromisoformat(job["orderTime"].replace("Z", "+00:00")),
                        "name":vessel_name.title(),
                        "etd":datetime.datetime.fromisoformat(job["etd"].replace("Z", "+00:00")),
                        "from":job["fromLocationShortCode"],
                        "to":job["toLocationShortCode"],
                        "agency":job["agencyName"],
                        "tug_from":tug_from,
                        "tug_to":tug_to
                        })
            if kwargs["print"]:
                print(mis_assigned_vessels)
            else:
                vessels_string = ""
                for i, item in enumerate(mis_assigned_vessels):
                    vessels_string = vessels_string + f", {item['name']}" if i != 0 else item['name']
                subject, from_email, to = f'{len(mis_assigned_vessels)} new mis-assigned vessels.', 'cool_bot@yoyoyo.com', 'saam_bot@googlegroups.com'
                text_content = f'Hi! \n As of last scan on {datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")}, there are {len(mis_assigned_vessels)} vessels that have been wrongfully assigned.'
                html_content =f'<div>Hi!<br>As of last scan on {datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")}, there are {len(mis_assigned_vessels)} vessels that have been wrongfully assigned.</div>'
                if len(mis_assigned_vessels) > 0:
                    text_content += ' The vessels are:\n\n{vessels_string}.'
                    html_content += '<h2>The vessels are:</h2><table style="font-family: arial, sans-serif; border-collapse: collapse; width: 100%;"><tr><th>Status</th><th>Order Time</th><th>Vessel Name</th><th>ETD</th><th>From</th><th>To</th><th>Agency</th><th>Tug From</th><th>Tug To</th></tr>'
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
                    html_content += '</table>'
                else:
                    text_content += 'Everything looks good!'
                    html_content += '<h2>Everything looks good!</h2>'
                msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
                msg.attach_alternative(html_content, "text/html")
                msg.send()

        except requests.HTTPError as err:
            if response.status_code == 404:
                print("The resource was not found!")
            else:
                print(f"An error occurred: {err}")
            with open("scan-error-logs.txt", "a") as log_file:
                log_file.write(f"{datetime.datetime.now(tz)}: {err}")

    def add_arguments(self, parser):
        parser.add_argument(
            '--print',
            action='store_true',
            help='Include to skip emailing the list and to just print it out.',
        )