#!/usr/bin/python
# -*- coding: utf-8 -*-

""" This file is part of B{Domogik} project (U{http://www.domogik.org}).

License
=======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
==============

This plugin manages scenarii, it provides MQ interface

Implements
==========


@author: Fritz SMH <fritz.smh at gmail.com>
@copyright: (C) 2007-2014 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

import traceback

import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr
import threading

#from domogik.common.plugin import Plugin

import zmq
from domogikmq.pubsub.subscriber import MQAsyncSub
from domogikmq.pubsub.publisher import MQPub
from zmq.eventloop.ioloop import IOLoop


PUBMSG = "irc public message"
PRIVMSG = "irc private message"

class IrcInterface():
    """ An irc interface for Domogik
    """

    def __init__(self):
        # TODO : use Interface when developped
        #Plugin.__init__(self, name = 'irc')
        self._name = "irc"

        ### Configuration
        # TODO : get from the configuration tools
        self.irc_server = "irc.freenode.net"
        self.irc_port = 6667
        self.irc_channel = "#domogik-offtopic"
        self.irc_user1_nick = "nestor"
        self.irc_user1_password = None
        self.irc_user2_nick = "samantha"  # in case user1 is already used
        self.irc_user2_password = None
        self.irc_reconnect_interval = 60

        # set the context
        # All elements that may be added in the request sent over MQ
        # * media (irc, audio, sms, ...)
        # * text (from voice recognition)
        # * location (the input element location : this is configured on the input element : kitchen, garden, bedroom, ...)
        # * identity (from face recognition)
        # * mood (from kinect or anything else) 
        # * sex (from voice recognition and post processing on the voice)
        self.context = {"media" : "irc",
                        "location" : None,
                        "identity" : None,
                        "mood" : None,
                        "sex" : None
                       }




        ### MQ
        print("Prepraring the MQ...")

        ## subscribe the MQ for interfaces inputs
        #self.sub = MQAsyncSub.__init__(self, self.zmq, self._name, ['interface.input'])

        ## MQ publisher 
        #self._mq_name = "interface-{0}.{1}".format(self._name, self.get_sanitized_hostname())
        #self.zmq = zmq.Context()
        #self.pub = MQPub(self.zmq, self._mq_name)


        print("Starting the bot....")
        #the_bot = Bot(self.irc_channel, self.irc_user1_nick, self.irc_server, self.irc_port, self.context, self.pub)
        the_bot = Bot(self.irc_channel, self.irc_user1_nick, self.irc_server, self.irc_port, self.context)
        # TODO : launch in a thread ?
        the_bot.start()

        #thr_bot = threading.Thread(None,
        #                           the_bot.start,
        #                           'bot',
        #                           (),
        #                           {})
        thr_bot.start()
        # TODO : register the thread

        # TODO : interface ready()


        # Review : set the MQ here instead of inside the bot ????




class Bot(irc.bot.SingleServerIRCBot, MQAsyncSub):
    """ The irc bot itself
        Based originally on testbot.py from https://bitbucket.org/jaraco/irc
    """

    def __init__(self, channel, nickname, server, port, context): ###, mq_pub):
        """
           @param channel : irc
           @param nickname : irc
           @param server : irc
           @param port : irc
           @param context : Domogik context for an interface
           @param mq_pub : MQPub object for publication over message queue
        """
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.context = context
        #self.mq_pub = mq_pub

        # MQ publisher 
        print("Prepare MQ publisher")
        self._mq_name = "interface-irc.{0}".format(self.get_sanitized_hostname())
        self.zmq = zmq.Context()
        self.mq_pub = MQPub(self.zmq, self._mq_name)

        # subscribe the MQ for interfaces inputs
        print("Subscribe to the MQ")
        MQAsyncSub.__init__(self, self.zmq, "irc", ['interface.output'])
        thr_ioloop = threading.Thread(None,
                                   IOLoop.instance().start,
                                   'bot',
                                   (),
                                   {})
        print("Start IOLoop in a thread...")
        thr_ioloop.start()

    #def start(self):
    #    print("Starting Bot...")
    #    irc.bot.SingleServerIRCBot.start(self)
    #    print("Starting IOLoop...")
    #    IOLoop.instance().start()

    def get_sanitized_hostname(self):
        """ TODO : remove when Interface will be used
        """
        return "foobar"

    def on_nicknameinuse(self, c, e):
        print("Nickname {0} already used, try to change it".format(c.get_nickname()))
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        print("Welcomed on the irc server. Preparing to join channels....")
        c.join(self.channel)

    def on_privmsg(self, c, e):
        print("PRIVMSG ({0}) > {1}".format(e.source.nick, e.arguments[0]))
        self.do_command(e, e.arguments[0], PRIVMSG)

    def on_pubmsg(self, c, e):
        print("PUBMSG  ({0}) > {1}".format(e.source.nick, e.arguments[0]))
        # On public channel, process only when explicitily called : "nestor : foo"
        a = e.arguments[0].split(":", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            self.do_command(e, a[1].strip(), PUBMSG)
        return

    def on_dccmsg(self, c, e):
        print("DCCMSG  ({0}) > {1}".format(e.source.nick, e))
        pass

    def on_dccchat(self, c, e):
        print("DCCCHAT ({0}) > {1}".format(e.source.nick, e))
        pass

    def do_command(self, e, cmd, location):
        """ Do a command depending on an entry message
            @param e : irc event
            @param cmd : what is said to the bot
            @location : private or public message
        """
        nick = e.source.nick
        c = self.connection

        if cmd == "disconnect":
            self.disconnect()
        elif cmd == "die":
            self.die()
        else:
            try:
                # send the request over MQ to the butler (or anything else :))
                request = self.context
                request["text" ] = cmd
                request["identity"] = nick
                request["location"] = location
                self.mq_pub.send_event('interface.input',
                                     request)

                # if ok, notify
                c.notice(nick, "Request sent over MQ with success")
            except:
                # if not ok, notify
                c.notice(nick, "Unable to send your request over the MQ : {0}".format(cmd))
                c.notice(nick, "The reason is :")
                for line in traceback.format_exc().split("\n"):
                    c.notice(nick, line)

    def on_message(self, msgid, content):
        """ When a message is received from the MQ (pub/sub)
        """
        print("Received message : {0}".format(content))
        c = self.connection
        if msgid == "interface.output":
            print("Received message : {0}".format(content))
            ### filter on location, media
            # if media not irc, don't process
            if content['media'] != "irc": 
                return
            # location
            if content['location'] == PUBMSG:
                c.privmsg(self.channel, "{0}".format(content['text']))
            elif content['location'] == PRIVMSG:
                c.privmsg(content['reply_to'], "{0}".format(content['text']))
            else:
                print("WARNING Invalid location received for irc media : {0}".format(content['location']))



if __name__ == "__main__":
    irc_interface = IrcInterface()
