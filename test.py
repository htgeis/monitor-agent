#coding=utf-8
#stdlib
import sys

#proj
from plugins.ServerPlugin import ServerPlugin
from utils.sendutil import Sender
from utils.util import Timer
import agentConfig
from utils.pluginUtil import get_plugin_class
agentConfig.initialize_logging('')

def main():
    timer=Timer()
    config=agentConfig.get_config()
    print(config)
    server = ServerPlugin()
    data = server.check()
    print(data)
    sender=Sender(port=config['recv_port'])
    sender.emit(data)
    print("send finished total cost time:"+str(timer.total()))
    return 0


def sendEmail():
    # coding:utf-8
    import smtplib
    from email.mime.text import MIMEText  # 引入smtplib和MIMEText

    host = 'smtp.163.com'  # 设置发件服务器地址
    port = 25  # 设置发件服务器端口号。注意，这里有SSL和非SSL两种形式
    sender = 'pub2015@163.com'  # 设置发件邮箱，一定要自己注册的邮箱
    pwd = 'qwer1234'  # 设置发件邮箱的密码，等会登陆会用到
    receiver = 'number_01@126.com'  # 设置邮件接收人，这里是我的公司邮箱
    body = '<h1>Hi</h1><p>test</p>'  # 设置邮件正文，这里是支持HTML的

    msg = MIMEText(body, 'html')  # 设置正文为符合邮件格式的HTML内容
    msg['subject'] = 'Hello Amy'  # 设置邮件标题
    msg['from'] = sender  # 设置发送人
    msg['to'] = receiver  # 设置接收人

    s = smtplib.SMTP(host, port)  # 注意！如果是使用SSL端口，这里就要改为SMTP_SSL
    #


    s.login(sender, pwd)  # 登陆邮箱
    res=s.sendmail(sender, receiver, msg.as_string())  # 发送邮件！

    print(res)  # 发送成功就会提示

if __name__ == '__main__':
    import re
    idc={"sdf":23,"e":3,"wu":1,"3":'12',"41":"te","5":"23a","%util":34,"%%":22,"%3%":23,"%354bn":23}
    for key in idc.keys():
        print(key)
    print('*'*20)
    for index,key in enumerate(idc):
        print(key)

        print(re.sub("%(?![0-9a-fA-F]{2})", "%25",key))
    print(idc)
    #sendEmail()

    content={}
    names=["hadoop-datanode3,60020,1479283727651", u"hadoop-datanodes电风扇6,60020,1478793456489"]
    print(repr(names))
    print(str(names))
    print(repr(names).decode('ascii').encode('utf-8'))
    print(str(names))
    import json
    na=json.dumps(names)
    content['live']=na
    print(na)
    print(type(na))
    print(content)
    print(json.dumps(content,ensure_ascii=False))
    print( sys.getdefaultencoding())
    # checkPlugin=get_plugin_class('ServerPlugin')
    # print(checkPlugin)
    # print(dir(checkPlugin))
    # checkPlugin = checkPlugin()
    # data = checkPlugin.check()
    # print(data)
    #sys.exit(main())
