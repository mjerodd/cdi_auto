from panos import network, firewall, policies, ha, updater, device
import xmltodict
from pprint import pprint
import subprocess, os, time
import requests
from environ import Env

env = Env()
Env.read_env()


class ChurchFirewall:
    zones = ['zone_to-pa-hub', 'zone-to-hub', 'zone-to-branch', 'zone-internet', 'zone-internal', 'noc_transit_router',
             'noc_infrastructure_mgmt',
             'corp_wireless_mgmt', 'corp_casino_operations', 'corp_client_audiovisual', 'corp_client_general',
             'corp_client_pos', 'corp_client_utility',
             'corp_client_voip', 'corp_facility_general', 'corp_printer_general', 'internet_public', 'internet_open',
             'corp_server_casino', 'corp_server_general', 'corp_server_voip', 'corp_tracd nsit_router'
             ]

    def __init__(self, firewall_ip):
        self.api_user = env("API_USER")
        self.api_password = env("API_PASSWORD")
        self.fw_host = firewall_ip
        self.fw_conn = firewall.Firewall(hostname=self.fw_host, api_username=self.api_user,
                                         api_password=self.api_password)
        self.fw_session = requests.Session()
        self.fw_token_response = self.fw_session.get(
            f'https://{firewall_ip}/api/?type=keygen&user={self.api_user}&password={self.api_password}',
            verify=False).text
        self.fw_token_dict = xmltodict.parse(self.fw_token_response)
        # self.fw_token = self.fw_token_dict['response']['result']['key']

    def initial_clean(self):
        vwire = network.VirtualWire(name="default-vwire")
        self.fw_conn.add(vwire)
        vwire.delete()
        ruleb = policies.Rulebase()
        self.fw_conn.add(ruleb)
        del_rule = policies.SecurityRule(name="rule1")
        ruleb.add(del_rule)
        del_rule.delete()

        trust = network.Zone(name="trust")
        untrust = network.Zone(name="untrust")
        self.fw_conn.add(trust)
        self.fw_conn.add(untrust)
        trust.delete()
        untrust.delete()

        int_1 = network.EthernetInterface(name="ethernet1/4")
        int_2 = network.EthernetInterface(name="ethernet1/5")
        self.fw_conn.add(int_1)
        self.fw_conn.add(int_2)
        int_1.delete()
        int_2.delete()

        vr = network.VirtualRouter(name="default")
        self.fw_conn.add(vr)
        vr.delete()
        self.fw_conn.commit()

    def ha_setup(self):
        ha_conf = ha.HighAvailability(enabled=True, group_id=10, state_sync=True, passive_link_state='auto',
                                      peer_ip='10.1.1.2', peer_ip_backup='10.1.1.6')
        ha_eth1 = network.EthernetInterface("ethernet1/7", mode="ha")
        ha_eth2 = network.EthernetInterface("ethernet1/8", mode="ha")
        self.fw_conn.add(ha_eth1)
        self.fw_conn.add(ha_eth2)
        ha_eth1.create()
        ha_eth2.create()
        self.fw_conn.commit()

        ha1_int = ha.HA1("10.1.1.1", "255.255.255.0", port="ethernet1/7")
        ha2_int = ha.HA2("10.2.2.2", "255.255.255.0", port="ethernet1/8")
        self.fw_conn.add(ha_conf)
        ha_conf.add(ha1_int)
        ha_conf.add(ha2_int)
        ha_conf.create()
        self.fw_conn.commit()

    def ping_fw(self):

        p_result = subprocess.run(['ping', '-c', '3', '-n', '192.168.1.11'], stdout=subprocess.PIPE, encoding='utf-8')
        loss = p_result.stdout.split('\n')[6]
        if '0% packet loss' in loss:
            print(loss)

    def set_mgmt(self):
        dev = device.SystemSettings(hostname='usMJT-fw01', ip_address='192.168.1.11', netmask='255.255.255.0',
                                    default_gateway='192.168.1.254',
                                    dns_primary='8.8.8.8', dns_secondary='8.8.8.1')
        self.fw_conn.add(dev)
        dev.create()
        self.fw_conn.commit()

    def disable_ztp(self):
        command = "set system ztp disable"
        self.fw_conn.op(cmd=command, xml=True)

        while True:
            time.sleep(60)
            if self.ping_fw() == False:
                break

        return "Firewall back online"

    def download_updates(self):

        updates = self.fw_conn.op(cmd='request content upgrade check', xml=True)
        format_update = xmltodict.parse(updates)
        update_list = format_update['response']['result']['content-updates']['entry']
        ver_list = []
        for vers in update_list:
            ver_num = vers['app-version'][-4:]
            ver_list.append(int(ver_num))

        new_ver = max(ver_list)
        print(new_ver)

        for i in update_list:
            if i['app-version'] in str(new_ver):
                print(f"Chose {i['app_version']}")
            '''
                downld_response = self.fw_conn.op(cmd='request content upgrade download latest', xml=True)
                dict_dwnld = xmltodict.parse(downld_response)
                print(dict_dwnld)
            '''

    def install_updates(self, filename):
        cmd = self.fw_session.get(
            f"https://{self.fw_host}/api/?type=op&cmd=<request><content><upgrade><install><file>{filename}</file></install></upgrade></content></request>&key={self.fw_token}",
            verify=False)
        form_install_resp = xmltodict.parse(cmd.text)
        pprint(form_install_resp)

        '''
        pprint(format_update['response']['result']['content-updates']['entry'], indent=3)


        info = self.fw_conn.op(cmd='request content upgrade info', xml=True)
        format_info = xmltodict.parse(info)
        pprint(format_info, indent=2)

        if updates.find('./result/updates-available/entry'):
            print("Downloading")

            print(info)
            self.fw_conn.op('request content upgrade download')
            self.fw_conn.op('request content upgrade install')
            self.fw_conn.commit()
        else:
            return None
    '''

    def enable_sdwan(self):
        sdwan_int = self.fw_conn.op(
            cmd='set network interface ethernet ethernet1/3 layer3 units ethernet1/1.1851 tag 1851', xml=True)
        dict_int = xmltodict.parse(sdwan_int)
        print(dict_int)

    def apply_bgp(self):

        url = f"https://{self.fw_host}/api"
        payload = f'key={self.fw_token}&type=config&action=set&xpath=%2Fconfig%2Fdevices%2Fentry%5B%40name%3D\'localhost.localdomain\'%5D%2Fnetwork%2Fvirtual-router%2Fentry%5B%40name%3D\'sdwan\'%5D%2Fprotocol&element=%3Cbgp%3E%3Crouting-options%3E%3Cgraceful-restart%3E%3Cenable%3Eyes%3C%2Fenable%3E%3C%2Fgraceful-restart%3E%3Cas-format%3E4-byte%3C%2Fas-format%3E%3C%2Frouting-options%3E%3Cenable%3Eyes%3C%2Fenable%3E%3Crouter-id%3E100.64.10.1%3C%2Frouter-id%3E%3Clocal-as%3E63415%3C%2Flocal-as%3E%3C%2Fbgp%3E%0A'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        response = self.fw_session.post(url, headers=headers, data=payload)

        print(response.text)

    def create_zone(self, zone):
        add_zone = network.Zone(name=zone, mode="layer3")
        self.fw_conn.add(add_zone)
        add_zone.create()

    def init_net(self):
        vr = network.VirtualRouter(name='sdwan')
        self.fw_conn.add(vr)
        vr.create()

        agg_int = network.AggregateInterface(name='ae1', mode='layer3', lacp_enable=True, lacp_mode='active',
                                             lacp_rate='slow')
        self.fw_conn.add(agg_int)
        agg_int.create()

        for zone in self.zones:
            self.create_zone(zone)
        self.fw_conn.commit()

        phys_int = network.EthernetInterface(name='ethernet1/5', mode='aggregate-group', aggregate_group='ae1')
        self.fw_conn.add(phys_int)
        phys_int.create()

        wan_phy_int = network.EthernetInterface(name='ethernet1/3', mode='layer3', lldp_enabled=True, enable_dhcp=True)
        self.fw_conn.add(wan_phy_int)
        wan_phy_int.create()

        wan_sub_int = network.Layer3Subinterface('ethernet1/3.1851', tag=1851, ip=('6.6.5.1/29',))
        self.fw_conn.add(wan_sub_int)
        wan_sub_int.create()
        wan_sub_int.set_zone('internet_public', update=True, running_config=True)
        wan_sub_int.set_virtual_router('sdwan', update=True, running_config=True)

        self.fw_conn.commit()

    def os_update(self, version):
        code = updater.SoftwareUpdater(self.fw_conn)
        code.download_install_reboot(version=version)
        # once program completes device reboots

    def disable_pan2(self):
        pan2 = device.SystemSettings(panorama2="1.1.1.1")
        self.fw_conn.add(pan2)
        pan2.delete()
        self.fw_conn.commit()

    def content_update(self):
        cont = updater.ContentUpdater(self.fw_conn)
        cont.download_install(version='latest')

    def get_cdi_dhcp(self):

        decom_ip = ["172.17.35.2", "172.17.64.23", "172.16.67.4", "172.16.32.100", "172.16.98.130", "172.17.130.19",
                    "172.17.226.100", "172.16.147.5", "172.17.176.12", "172.17.160.231", "172.16.4.20", "172.16.115.5",
                    "172.17.234.100", "172.16.131.14", "172.16.9.219", "172.17.254.2", "172.16.4.21", "172.16.9.220",
                    "172.16.9.10", "172.16.9.150", "172.16.4.21", "172.17.160.230", "172.16.4.25", "172.16.9.130", "172.16.9.241",
                    "172.16.4.233", "172.16.4.245", "172.16.4.232", "172.16.4.231"]

        dhcp_info = self.fw_conn.op('show dhcp server settings "all"', xml=True)
        dict_dhcp = xmltodict.parse(dhcp_info)
        dhcp_list = dict_dhcp['response']['result']['entry']
        for entry in dhcp_list:
            print(f"FW - {self.fw_host}\tInterface: {entry['@name']}")
            print("********************************************************")
            print(f"Primary DNS: {entry['dns1']}")
            print(f"Secondary DNS: {entry['dns2']}")
            print("********************************************************\n")
            if entry['dns1'] or entry['dns2'] in decom_ip:
                print(f"[*] Invalid DNS detected on {self.fw_host} {entry['@name']}")
