from time import sleep

from models import Message, DontSendEntry, MessageLog


## configuration settings
# @@@ eventually move to settings.py

# when queue is empty, how long to wait (in seconds) before checking again
EMPTY_QUEUE_SLEEP = 30



def send_all():
    """
    Send all eligible messages in the queue.
    """
    
    for message in Message.objects.send_order():
        if DontSendEntry.objects.has_address(message.to_address):
            print "skipping email to %s as on don't send list " % message.to_address
            MessageLog.objects.log(message, 2) # @@@ avoid using literal result code
            message.delete()
        else:
            print "sending message '%s' to %s" % (message.subject, message.to_address)
            MessageLog.objects.log(message, 1) # @@@ avoid using literal result code
            message.delete()



def send_loop():
    """
    Loop indefinitely, checking queue at intervals of EMPTY_QUEUE_SLEEP and
    sending messages if any are on queue.
    """
    
    while True:
        while not Message.objects.all():
            print 'sleeping for %s seconds before checking queue again' % EMPTY_QUEUE_SLEEP
            sleep(EMPTY_QUEUE_SLEEP)
        send_all()
