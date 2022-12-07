#python3

import ts3
import openai
import time
import conf

openai.api_key = conf.open_api_key
channel_name = conf.ts3_channel_name

# Connect to the server
with ts3.query.TS3Connection(conf.ts3_server_ip) as ts3conn:
    # Authenticate with the server
    ts3conn.login(
        client_login_name=conf.ts3_server_query_username,
        client_login_password=conf.ts3_server_query_passwd
    )

    # Join the server
    ts3conn.use(sid=1)
    
    
    #get the channel list
    channels = ts3conn.channellist()
    
    #find the channel
    channel = next(channel for channel in channels if channel["channel_name"] == channel_name)
    
    #get my data
    serverQueryName = ts3conn.whoami()[0]['client_nickname']
    serverQueryID = ts3conn.whoami()[0]['client_id']
    
    #move the user to the channel
    ts3conn.clientmove(cid=channel["cid"], clid=serverQueryID)
    
    #say hello world in chat
    completions = openai.Completion.create(
        engine="text-davinci-003",
        prompt=conf.intro_message,
        max_tokens=100,
        n=1,
        stop=None
    )
    ts3conn.sendtextmessage(targetmode=2, target=channel["cid"], msg=completions.choices[0].text)

    # Register for the event.
    ts3conn.servernotifyregister(event="textchannel")
    ts3conn.servernotifyregister(event="channel", id_=channel["cid"])

    timeouts = 0
    while True:
        ts3conn.send_keepalive()

        try:
            # This method blocks, but we must sent the keepalive message at
            # least once in 5 minutes to avoid the sever side idle client
            # disconnect. So we set the timeout parameter simply to 1 minute.
            event = ts3conn.wait_for_event(timeout=60)
            print(event)
            print(event[0])
            
            if 'invokername' in event[0]:
            
                if event[0]['invokername'] == serverQueryName:    
                    continue
            
                msg = event.parsed[0]['msg']
                print(event.parsed[0]['msg'])
                
                image_prefix = "Image:"
                
                if msg.startswith(image_prefix):
                    print("Generating Image")
                    print(msg[len(image_prefix):])
                    response = openai.Image.create(
                      prompt=msg[len(image_prefix):],
                      n=1,
                      size="1024x1024"
                    )
                    image_url = response['data'][0]['url']
                    ts3conn.sendtextmessage(targetmode=2, target=channel["cid"], msg=image_url)
                else:
                    completions = openai.Completion.create(
                        engine="text-davinci-003",
                        prompt=event.parsed[0]['msg'],
                        max_tokens=1024,
                        n=1,
                        stop=None
                    )

                    # print the generated text
                    print(completions.choices[0].text)
                    ts3conn.sendtextmessage(targetmode=2, target=channel["cid"], msg=completions.choices[0].text)
                    
            else:
                name = ts3conn.clientinfo(clid=event[0]['clid'])[0]['client_nickname']
                completions = openai.Completion.create(
                        engine="text-davinci-003",
                        prompt="Welcome {} to the channel.".format(name),
                        max_tokens=1024,
                        n=1,
                        stop=None
                    )
                ts3conn.sendtextmessage(targetmode=2, target=channel["cid"], msg=completions.choices[0].text)
            
            
        except ts3.query.TS3TimeoutError:
            timeouts+=1
            if timeouts == 5:
                completions = openai.Completion.create(
                        engine="text-davinci-003",
                        prompt=conf.forgotten_message_prompt,
                        max_tokens=100,
                        n=1,
                        stop=None
                    )
                ts3conn.sendtextmessage(targetmode=2, target=channel["cid"], msg=completions.choices[0].text)
                timeouts = 0

