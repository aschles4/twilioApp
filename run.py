from __future__ import print_function
import boto3

symptoms = {"1": "Headache", "2": "Dizziness", "3": "Nausea", "4": "Fatigue", "5": "Sadness"}
ratings = {"1": "mild", "2": "mild", "3": "moderate", "4": "severe"}
client = boto3.resource('dynamodb')
table = client.Table("study")


def lambda_handler(event, context):
    print("Received event: " + str(event))
    message = event['Body']
    number = event['From']
    resp = ''
    stepAns = {}
    ratingAns = {}

    # Track: Step, StepAnswers, Status, rounds, symptom selections
    # Status: In-Progress, Complete
    user = findUser(number)
    if user is not None:
        stepAns = user['sym_selections']
        ratingAns = user['ratings_selections']

    if message == 'START' and user is None:
        user = {
            'number': number,
            'status': 'In-Progress',
            'step': 1,
            'round': 1,
            'sym_selections': {},
            'ratings_selections': {},
        }
        # Prep user dic at step 1
        resp = defineSMSMessage("Welcome to the study") + \
               defineSMSMessage(
                   "Please indicate your symptom (1)Headache, (2)Dizziness, (3)Nausea, (4)Fatigue, (5)Sadness, (0)None")

    elif user['status'] == 'In-Progress':
        if user['step'] == 1:
            if message == "0":
                user['status'] = 'Complete'
                resp = defineSMSMessage("Thank you and we will check with you later.")
            elif message in "12345":
                stepAns = {**stepAns, str(user['round']): message}
                user['sym_selections'] = stepAns
                user['step'] = 2
                resp = defineSMSMessage(
                    "On a scale from 0 (none) to 4 (severe), how would you rate your " + symptoms.get(
                        message) + " in the last 24 hours?")
            else:
                resp = defineSMSMessage("Please enter a number from 0 to 5")
        elif user.get('step') == 2:
            if message in "01234":
                ratingAns = {**ratingAns, str(user['round']): message}
                user['ratings_selections'] = ratingAns
                if message == "0":
                    resp = defineSMSMessage("You do not have a " + symptoms[stepAns[str(user['round'])]])
                elif message in "1234":
                    resp = defineSMSMessage('You have a ' + ratings.get(message) + ' ' + symptoms[stepAns[str(user['round'])]])

                if user['round'] == 3:
                    user['status'] = 'Complete'
                    resp = resp + defineSMSMessage('Thank you and see you soon')
                else:
                    resp = resp + defineSMSMessage('Please indicate your symptom ' + selections(stepAns))
                user['round'] += 1
                user['step'] = 1
            else:
                resp = defineSMSMessage("Please enter a number from 0 to 4")
    else:
        resp = defineSMSMessage("Please provide a valid message")

    table.put_item(Item=user)
    return createXMLMessage(resp)


def selections(list):
    resp = ''
    for k, v in symptoms.items():
        if k not in list.values():
            resp += '(' + k + ')' + v + ', '
    resp += '(0)None'
    return resp


def findUser(number):
    response = table.get_item(Key={'number': number})
    if 'Item' in response:
        return response['Item']
    else:
        return None


def defineSMSMessage(msg):
    return '<Message>' + msg + '</Message>'


def createXMLMessage(msg):
    return '<?xml version=\"1.0\" encoding=\"UTF-8\"?>' \
           '<Response>' + msg + '</Response>'

