import html
import apprise


def send_notification(apprise_url, message):
    try:
        # Escape the message for markdown formatting
        safe_message = html.escape(message)

        # Initialize Apprise and set the notification URL
        notifier = apprise.Apprise()
        notifier.add(apprise_url)

        # Send the notification
        response = notifier.notify(body=safe_message, title="JobNotify Notification")

        # If response is 0, it means failure in sending the notification
        if response == 0:
            return False
        return True
    except Exception as e:
        print(f"Error sending notification: {str(e)}")
        return False


def send_welcome_message(apprise_url, channel_name):
    """
    Send a welcome message for a newly created channel.

    :param apprise_url: The Apprise URL to send the notification
    :param channel_name: The name of the channel to include in the welcome message
    :return: None
    """
    welcome_message = f"Welcome to JobNotify! We are excited to have you onboard with the {channel_name} channel."
    return send_notification(apprise_url, welcome_message)
