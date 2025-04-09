from django.shortcuts import render, redirect
from .forms import CoreTempForm, IntDescriptionForm, IosUpgradeForm, PaloForm, PaloOsUpgradeForm
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_config, netmiko_send_command, netmiko_file_transfer
from nornir_utils.plugins.functions import print_result
from nornir_jinja2.plugins.tasks import template_file
from .ChurchFirewall import ChurchFirewall

# Create your views here.

cores_dict = [
	{
	"core01":
        {
		"hostname": "10.0.0.254",
		"groups": ["lab_group"]
        },
	"data": {
			"mgmt_ip": "10.32.40.131",
			"site_id": "DCD",
			"switch_num": "1",
			"mgmt_mask": "24",
			"mgmt_gw": "10.32.112.254",
			"tacacs_key": "nc;eikzm882ml#czPs1uu",
			"telecom_space": "B",
			"vpc_peer_src_ip": "10.188.120.0",
			"vpc_peer_dest_ip": "10.188.120.1",
			"logging_srvr": "172.20.5.5"
	}

	},
	{
		"core02":
			{
				"hostname": "192.168.1.58",
				"groups": ["lab_group"]
			},
		"data": {
			"mgmt_ip": "10.32.40.132",
			"site_id": "DCD",
			"switch_num": "2",
			"mgmt_mask": "24",
			"mgmt_gw": "10.32.112.254",
			"tacacs_key": "nc;eikzm882ml#czPs1uu",
			"telecom_space": "B",
			"vpc_peer_src_ip": "10.188.120.1",
			"vpc_peer_dest_ip": "10.188.120.0",
			"logging_srvr": "172.20.5.5"
		}

	},
]


def index(request):
    return render(request, "net_app/index.html")


def os_trans(task):
    file_name = task.host.get('img')
    result = task.run(task=netmiko_file_transfer, source_file=file_name, dest_file=file_name, direction='put')
    return result


def send_to_switch(task):
    nr = InitNornir(
        config_file="/home/marv/PycharmProjects/Work_Automation/app/net_app/yaml_files/ints_config.yaml")
    code_pres = task.run(task=netmiko_send_command, enable=True, command_string="dir flash: | in .bin")
    try:
        if '17.06.05' in code_pres.result:
            print("No Need for File Transfer")
        else:
            vty_comm = ['line vty 0 15', 'exec-timeout 60']
            up_exec = task.run(task=netmiko_send_config, config_commands=vty_comm)
            print_result(up_exec)
            print(f"Starting Download For {task.host}")
            fin_result = nr.run(task=os_trans)
            print_result(fin_result)

    except OSError:
        print(f"File Transfer for {task.host} Complete")

def get_ints(task):
    cdp_result = task.run(task=netmiko_send_command, command_string="show cdp neighbor", use_textfsm=True)
    task.host["facts"] = cdp_result.result
    print(task.host["facts"])

    for fact in task.host["facts"]:
        if fact['platform'] == "IP Phone":
            continue
        neighbor = fact['neighbor']
        loc_int = fact['local_interface']
        rem_int = fact['neighbor_interface']
        task.run(task=netmiko_send_config, config_commands=[f"int {loc_int}", f"description {neighbor} - {rem_int}"])


def nex_conf(task):
    template = task.run(task=template_file, template="nx_template.j2", path="/home/marv/PycharmProjects/nornir_automation/net_automation/net_app/jinja_templates/")
    task.host["stage_conf"] = template.result
    rendered = task.host["stage_conf"]
    configuration = rendered
    with open(f"{task.host}_conf.txt", "w") as f:
        f.write(configuration)

    task.run(task=netmiko_send_config, read_timeout=90, config_file=f"{task.host}_conf.txt")


def core_ip(subnet):
    ip_add = subnet
    split_ip = ip_add.split(".")
    split_ip[3] = "31"
    core1_ip = ".".join(split_ip)
    split_ip[3] = "32"
    core2_ip = ".".join(split_ip)
    split_ip[3] = "254"
    core_gw = ".".join(split_ip)
    return [core1_ip, core2_ip, core_gw]


def core_temp(request):
    if request.method == 'POST':
        '''
        form = CoreTempForm(request.POST)

        if form.is_valid():
            print(form.cleaned_data)

            cor_ips = core_ip(form.cleaned_data['mgmt_subnet'])
            cores_dict[0]["data"]["mgmt_ip"] = cor_ips[0]
            cores_dict[1]["data"]["mgmt_ip"] = cor_ips[1]
            cores_dict[0]["data"]["mgmt_gw"] = cor_ips[2]
            cores_dict[1]["data"]["mgmt_gw"] = cor_ips[2]

            with open("./net_app/yaml_files/hosts6.yaml", "w") as f:
                yaml.dump(cores_dict, f)
            '''
        nr = InitNornir(
                config_file="/home/marv/PycharmProjects/Work_Automation/app/net_app/yaml_files/ini_config.yaml")
        result = nr.run(task=nex_conf)
        print_result(result)
        return redirect("thank-you")
    else:
        form = CoreTempForm()
        context = {"form": form}
        return render(request, "net_app/core_build.html", context=context)


def thank_you(request):
    return render(request, "net_app/thanks.html")


def int_descriptions(request):
    if request.method == 'POST':
        nr = InitNornir(
            config_file="/home/marv/PycharmProjects/Work_Automation/app/net_app/yaml_files/ints_config.yaml")
        result = nr.run(task=get_ints)
        print_result(result)
        return redirect("thank-you")
    else:
        form = IntDescriptionForm()
    return render(request, "net_app/int_description.html", {"form": form})


def ios_up(request):
    if request.method == 'POST':
        try:
            nr = InitNornir(
                config_file="/home/marv/PycharmProjects/Work_Automation/app/net_app/yaml_files/ints_config.yaml")
            results = nr.run(task=send_to_switch)
            print_result(results)
        except OSError:
            print(f"File Transfer Complete")
        return redirect("thank-you")
    else:
        form = IosUpgradeForm()
        return render(request, "net_app/ios-upgrade.html", {"form": form})


def ini_fw_auto(request):
    if request.method == 'POST':
        form = PaloForm(request.POST)

        if form.is_valid():
            print(form.cleaned_data)
            conf_fw = ChurchFirewall(form.cleaned_data['firewall_ip'])
            conf_fw.initial_clean()
            conf_fw.init_net(form.cleaned_data['wan_ip'])
            return redirect('index')
    else:
        form = PaloForm()
        context = {'form': form}
    return render(request, "net_app/firewall_auto.html", context=context)


def fw_os_auto(request):
    if request.method == 'POST':
        form = PaloOsUpgradeForm(request.POST)

        if form.is_valid():
            print("valid")
            print(form.cleaned_data)
            fw_ver = form.cleaned_data['version']
            #try:
            target = list(form.cleaned_data.values())[0]
            print(target)
            target_list = target.split(',')
            print(target_list)

            for fw in target_list:
                print(fw)
                cf = ChurchFirewall(fw)
                cf.os_update(fw_ver)

            #except Exception as e:
            #   print("Error: ", e)

            return redirect('index')
    else:
        form = PaloOsUpgradeForm()
        context = {'form': form}
    return render(request, "net_app/firewall_auto.html", context=context)


def fw_tools(request):
    return render(request, "net_app/fw_tools.html")