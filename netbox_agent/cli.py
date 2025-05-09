import sys
from packaging import version
import netbox_agent.dmidecode as dmidecode
from netbox_agent.config import config
from netbox_agent.config import netbox_instance as nb
from netbox_agent.logging import logging  # NOQA
from netbox_agent.misc import is_tool
from netbox_agent.vendors.dell import DellHost
from netbox_agent.vendors.generic import GenericHost
from netbox_agent.vendors.hp import HPHost
from netbox_agent.vendors.qct import QCTHost
from netbox_agent.vendors.supermicro import SupermicroHost
from netbox_agent.virtualmachine import VirtualMachine, is_vm

REQUIRED_TOOLS = {
    "dmidecode": "Hardware information gathering",
    "ipmitool": "IPMI interface",
    "ethtool": "Network interface information",
    "lshw": "Hardware information gathering"
}

def check_dependencies():
    missing_tools = []
    for tool, description in REQUIRED_TOOLS.items():
        if not is_tool(tool):
            missing_tools.append(f"{tool} ({description})")
    
    if missing_tools:
        logging.error("Missing required tools:")
        for tool in missing_tools:
            logging.error(f"- {tool}")
        sys.exit(1)

MANUFACTURERS = {
    "Dell Inc.": DellHost,
    "HP": HPHost,
    "HPE": HPHost,
    "Supermicro": SupermicroHost,
    "Quanta Cloud Technology Inc.": QCTHost,
}


def run(config):
    check_dependencies()
    
    dmi = dmidecode.parse()

    if config.virtual.enabled or is_vm(dmi):
        if config.virtual.hypervisor:
            raise Exception("This host can't be a hypervisor because it's a VM")
        if not config.virtual.cluster_name:
            raise Exception("virtual.cluster_name parameter is mandatory because it's a VM")
        server = VirtualMachine(dmi=dmi)
    else:
        if config.virtual.hypervisor and not config.virtual.cluster_name:
            raise Exception(
                "virtual.cluster_name parameter is mandatory because it's a hypervisor"
            )
        manufacturer = dmidecode.get_by_type(dmi, "Chassis")[0].get("Manufacturer")
        server_class = MANUFACTURERS.get(manufacturer, GenericHost)
        server = server_class(dmi=dmi)

    if version.parse(nb.version) < version.parse("3.7"):
        print("netbox-agent is not compatible with Netbox prior to version 3.7")
        return 1

    if (
        config.register
        or config.update_all
        or config.update_network
        or config.update_location
        or config.update_inventory
        or config.update_psu
    ):
        server.netbox_create_or_update(config)
    if config.debug:
        server.print_debug()
    return 0


def main():
    return run(config)


if __name__ == "__main__":
    sys.exit(main())
