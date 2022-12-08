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
    
    #find the channel
    #channel = next(channel for channel in channels if channel["channel_name"] == channel_name)
    
    #get my data
    serverQueryName = ts3conn.whoami()[0]['client_nickname']
    serverQueryID = ts3conn.whoami()[0]['client_id']  

    timeouts = 0
    channel = None
    
    while True:
        ts3conn.send_keepalive()
        
        #join the channel with the most people in it
        
        #get the channel list
        channels = ts3conn.channellist()
        channel_changed = False
        
        #update the channel
        if channel is not None:
            for chan in channels:
                if chan["cid"] == channel["cid"]:
                    channel = chan
        
        for chan in channels:
            if channel is None:
                channel = chan
                channel_changed = True

            clients = chan["total_clients"]

            if int(clients) > int(channel["total_clients"]):
                channel = chan
                channel_changed = True
        
        #get channel id
        channel_id = int(channel["cid"])
        
        if channel_changed:
            print("Joining channel: {}".format(channel["channel_name"]))
            
            ts3conn.clientmove(cid=channel_id, clid=serverQueryID)
            
            #unregister to events
            ts3conn.servernotifyunregister()
            
            # Register for the event.
            ts3conn.servernotifyregister(event="textchannel", id_=channel_id)
            ts3conn.servernotifyregister(event="channel", id_=channel_id)
    
            if conf.use_into_message:
                    completions = openai.Completion.create(
                        engine="text-davinci-003",
                        prompt=conf.intro_message,
                        max_tokens=100,
                        n=1,
                        stop=None
                    )
                    ts3conn.sendtextmessage(targetmode=2, target=channel["cid"], msg=completions.choices[0].text)
       

        try:
            # This method blocks, but we must sent the keepalive message at
            # least once in 5 minutes to avoid the sever side idle client
            # disconnect. So we set the timeout parameter simply to 1 minute.
            event = ts3conn.wait_for_event(timeout=60)
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
            if conf.user_forgotten_message and timeouts == conf.forgotten_message_interval:
                completions = openai.Completion.create(
                        engine="text-davinci-003",
                        prompt=conf.forgotten_message_prompt,
                        max_tokens=100,
                        n=1,
                        stop=None
                    )
                ts3conn.sendtextmessage(targetmode=2, target=channel["cid"], msg=completions.choices[0].text)
                timeouts = 0

