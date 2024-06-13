import sys
import os
import re
import io


debug = True # Turn on to see debugging messages
ipv4_prefix_regex1=r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}"
ipv4_prefix_regex2=r"([1-9][0-9]?|1[0-9][0-9]|(2[0-1][0-9]|22[0-3]))(\.([1-9]?[0-9]|1[0-9][0-9]|(2[0-4][0-9]|25[0-5]))){3}\/(3[0-2]|[1-2][0-9]|[1-9])"

def print_help():
    print('Usage: compare_geobases.py path_to_first_geobase.csv path_to_second_geobase.csv [-country locations_file.csv | -city locations_file.csv]')

def parse_locations(input_locations_file_path: str, city_type=False):
    locations_dict = {}
    with io.open(input_locations_file_path, encoding='utf-8') as input_file:
        lines = input_file.readlines()
        for line in lines[1:]:
            geo_id = line.split(',')[0]
            country_name = line.split(',')[5]
            locations_dict[geo_id] = f'{country_name}'
            if city_type:
                city_name = line.split(',')[10]
                locations_dict[geo_id] += f'/{city_name}'
    return locations_dict
        
        
        
def check_geolite2_prefixes_func(input_file_path):
    # Open, read and validate input file
    input_file_lines = []
    proc_file_lines = []
    clean_prefix_lines = []
    header_line = ""
    prefix_list = set()
    prefix_lines = 0
    prefix_length_set = set()
    prefix_overlap_dict = {}
    error_index_list = []
    error_count = 0
    with open(input_file_path) as input_file:
        print("Processing input file \"" + str(input_file_path) + "\"...")
        input_file_lines = input_file.readlines()
        for index, line in enumerate(input_file_lines, start=1):
            line = line.replace('\n', '').replace('\r', '')

            if (len(error_index_list) > 100):
                print("Error: input file contains too many lines without IPv4 prefixes.\n")
                sys.exit()

            if (index == 1):
                if (len(re.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", line)) > 1):
                    print("  Info: line " + str(index) + ": found CSV header \"" + "|".join(str(val) for val in re.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", line)) + "\".")
                    header_line = line
                    proc_file_lines.append(line)
                    continue
            if (not re.search(ipv4_prefix_regex1,line)):
                print("  Error: line " + str(index) + ": no IPv4-prefix found in text \"" + str(line) + "\".")
                proc_file_lines.append("")
                error_index_list.append(index)
                continue
            else:
                proc_file_lines.append(line)
                prefix_lines += 1
        
        error_count += len(error_index_list)

        if (prefix_lines == 0):
            print("Error: input file contains no IPv4 prefixes.\n")
            sys.exit()

        if (len(re.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", proc_file_lines[0])) > 1):
            print("Input file is in CSV format with " + str(len(re.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", proc_file_lines[0]))) + " column(s) and contains "\
                + str(len(input_file_lines)) + " line(s) and " + str(prefix_lines) + " prefix(es).")
        else:
            print("Input file is a plain text and contains total " + str(len(input_file_lines)) + " line(s) and " + str(prefix_lines) + " prefix(es).")

    if (len(proc_file_lines) > 0):
        # Validate prefixes and create unique set
        print("Validating prefixes...")
        csv_columns = len(re.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", proc_file_lines[0]))
        error_index_list = []
        for index, line in enumerate(proc_file_lines, start=1):
            if (len(line) > 0):
                # If file is in CSV format
                if (csv_columns > 1):
                    # Check if line has not the same number of fileds as header
                    if (len(re.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", line)) != csv_columns):
                        error_index_list.append(index)
                        print("  Error: line " + str(index) + ": CSV format error, line contains " + str(len(re.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", line))) + " columns(s).")
                    original_line = line
                    line = re.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", line)[0]
                # Check if prefix is incorrect
                if (re.search(ipv4_prefix_regex1,line) and not re.match(r"^" + ipv4_prefix_regex2 + r"$",line)):
                    error_index_list.append(index)
                    print("  Error: line " + str(index) + ": IPv4-prefix \"" + str(re.search(r"^.*" + ipv4_prefix_regex1 + r".*$",line).group()) + "\" is invalid.")
                # Check if prefix is unique
                elif (re.match(r"^" + ipv4_prefix_regex2 + r"$",line)):
                    prefix = re.match(r"^" + ipv4_prefix_regex2 + r"$",line).group()
                    prefix_length = prefix.split("/")[1]
                    prefix_octets = prefix.split("/")[0].split(".")            
                    prefix_net_bin = (int(prefix_octets[0]) << 24) | (int(prefix_octets[1]) << 16) | (int(prefix_octets[2]) << 8) | int(prefix_octets[3])
                    prefix_mask_bin = (0xffffffff - (1 << (32 - int(prefix_length))) + 1)
                    # Check if prefix address is correct with specifed prefix length
                    if ((prefix_net_bin & prefix_mask_bin) != prefix_net_bin):
                        prefix2_bin = prefix_net_bin & prefix_mask_bin
                        prefix2 = str(int((prefix2_bin >> 24) & 0x000000ff)) + "." + str(int((prefix2_bin >> 16) & 0x000000ff)) + "." + str(int((prefix2_bin >> 8) & 0x000000ff))\
                            + "." + str(int(prefix2_bin & 0x000000ff)) + "/" + str(prefix_length)
                        print("  Error: line " + str(index) + ": wrong IPv4-prefix address \"" + str(prefix) + "\", for specifed prefix length prefix should be " + str(prefix2))
                        # prefix = prefix2
                        error_index_list.append(index)
                        continue
                    if (int(prefix.split("/")[1]) not in prefix_length_set):
                        prefix_length_set.add(int(prefix.split("/")[1]))
                    if (prefix in prefix_list):
                        print("  Error: line " + str(index) + ": IPv4-prefix \"" + str(prefix) + "\" duplicated in input file.")
                    else:
                        prefix_list.add(prefix)
                        if (csv_columns > 1):
                            clean_prefix_lines.append(original_line)
        
        error_count += len(error_index_list)

        # Check if existing prefixes are subset of any other
        for prefix in sorted(prefix_list):
            prefix_length = prefix.split("/")[1]
            prefix_octets = prefix.split("/")[0].split(".")            
            prefix_net_bin = (int(prefix_octets[0]) << 24) | (int(prefix_octets[1]) << 16) | (int(prefix_octets[2]) << 8) | int(prefix_octets[3])
            for variable_length in sorted(prefix_length_set):
                # If we reached original lenght, exiting
                if (int(variable_length) >= int(prefix_length)):
                    break
                prefix3_mask_bin = (0xffffffff - (1 << (32 - int(variable_length))) + 1)
                prefix3_bin = prefix_net_bin & prefix3_mask_bin
                prefix3 = str(int((prefix3_bin >> 24) & 0x000000ff)) + "." + str(int((prefix3_bin >> 16) & 0x000000ff)) + "." + str(int((prefix3_bin >> 8) & 0x000000ff))\
                    + "." + str(int(prefix3_bin & 0x000000ff)) + "/" + str(variable_length)
                if (prefix3 in prefix_list):
                    if (str(prefix3) not in prefix_overlap_dict):
                        prefix_overlap_dict[str(prefix3)] = list()
                    prefix_overlap_dict[str(prefix3)].append(str(prefix))
        for key in sorted(prefix_overlap_dict):
            print("  Error: IPv4-prefix \"" + str(key) + "\" in input file overlaps with following subprefixes: " + ", ".join(value for value in prefix_overlap_dict[key]))
        print("Validation finished.")
        return(error_count, header_line, clean_prefix_lines)


class BinaryTree:
    def __init__(self, prefix, data):
        octets = prefix.split("/")[0].split(".")
        self.prefix = prefix
        self.address = (int(octets[0]) << 24) | (int(octets[1]) << 16) | (int(octets[2]) << 8) | int(octets[3])
        self.netmask = int(prefix.split("/")[1])
        self.data = data
        self.left = None
        self.right = None

    def set_prefix_data(self, prefix, data):
        if (prefix is None) or (data is None):
            return None
        netmask = int(prefix.split("/")[1])
        netmask_bits = (0xffffffff - (1 << (32 - int(netmask))) + 1)
        octets = prefix.split("/")[0].split(".")     
        address = (int(octets[0]) << 24) | (int(octets[1]) << 16) | (int(octets[2]) << 8) | int(octets[3])
        if ((netmask_bits & address) == address):
            node = self
            for i in range(1, netmask + 1):
                direction = ((address >> (32 - i)) & 0x1)
                if node.left is None:
                    children_left_address = node.address
                    children_left_prefix = str(int((children_left_address >> 24) & 0x000000ff)) + "." + str(int((children_left_address >> 16) & 0x000000ff))\
                        + "." + str(int((children_left_address >> 8) & 0x000000ff)) + "." + str(int(children_left_address & 0x000000ff)) + "/" + str(i)
                    node.left = BinaryTree(children_left_prefix, "")
                if node.right is None:
                    children_right_address = node.address | (0x1 << (32 - i))
                    children_right_prefix = str(int((children_right_address >> 24) & 0x000000ff)) + "." + str(int((children_right_address >> 16) & 0x000000ff))\
                        + "." + str(int((children_right_address >> 8) & 0x000000ff)) + "." + str(int(children_right_address & 0x000000ff)) + "/" + str(i)
                    node.right = BinaryTree(children_right_prefix, "")
                if (direction == 0):
                    node = node.left
                else:
                    node = node.right
            node.data = data
        else:
            raise Exception("Invalid prefix/prefix length: " + prefix + ". All host bits should be 0.")

    def get_prefix_data(self, prefix):
        if (prefix is None):
            return None
        netmask = int(prefix.split("/")[1])
        octets = prefix.split("/")[0].split(".")     
        address = (int(octets[0]) << 24) | (int(octets[1]) << 16) | (int(octets[2]) << 8) | int(octets[3])
        
        prefix_mask_bin = (0xffffffff - (1 << (32 - int(netmask))) + 1)
        address = address & prefix_mask_bin
        
        node = self
        for i in range(1, netmask + 1):
            direction = ((address >> (32 - i)) & 0x1)
            if (direction == 0):
                if node.left is None:
                    return None
                else:
                    node = node.left
            else:
                if node.right is None:
                    return None
                else:
                    node = node.right
        return([node.prefix, "{:032b}".format(node.address), node.netmask, node.data])

    def get_prefix_data2(self, prefix):
        if (prefix is None):
            return None
        netmask = int(prefix.split("/")[1])
        octets = prefix.split("/")[0].split(".")     
        address = (int(octets[0]) << 24) | (int(octets[1]) << 16) | (int(octets[2]) << 8) | int(octets[3])
        prefix_mask_bin = (0xffffffff - (1 << (32 - int(netmask))) + 1)
        address = address & prefix_mask_bin
        node = self
        for i in range(1, netmask + 1):
            direction = ((address >> (32 - i)) & 0x1)
            if (direction == 0):
                if node.left is None:
                    return([[prefix, "{:032b}".format(address), netmask, node.data]])
                else:
                    node = node.left
            else:
                if node.right is None:
                    return([[prefix, "{:032b}".format(address),netmask, node.data]])
                else:
                    node = node.right
        if not node.data:
            def get_subtree_data(node):
                result = []
                if node.left and node.left.data:
                    result.append([node.left.prefix, "{:032b}".format(node.left.address), node.left.netmask, node.left.data])
                if node.right and node.right.data:
                    result.append([node.right.prefix, "{:032b}".format(node.right.address), node.right.netmask, node.right.data])
                if not node.left and not node.right:
                    return []
                return result + get_subtree_data(node.left) + get_subtree_data(node.right)
            return(get_subtree_data(node))
        else:
            return([[node.prefix, "{:032b}".format(node.address), node.netmask, node.data]])

    def check_subtree_data(self):
        root = self
        if root is None:
            return(0)
        queue = []
        if root.left is not None:
            queue.append(root.left)
        if root.right is not None:
            queue.append(root.right)
        while len(queue) > 0:
            cur_node = queue.pop(0)
            if (cur_node.data != ""):
                print("  Prefix " + root.prefix + " overlaps with prefix " + cur_node.prefix)
                return (1)
            else:
                if cur_node.left is not None:
                    queue.append(cur_node.left)
                if cur_node.right is not None:
                    queue.append(cur_node.right)
        return(0)

    def remove_data_overlay(self):
        root = self
        if root is None:
            return
        queue = [root]
        while len(queue) > 0:
            cur_node = queue.pop(0)
            if ((cur_node.data != "") and ((cur_node.check_subtree_data() == 1))):
                if cur_node.left is not None:
                    queue.append(cur_node.left)
                    if cur_node.left.data == "": cur_node.left.data = cur_node.data
                if cur_node.right is not None:
                    queue.append(cur_node.right)
                    if cur_node.right.data == "": cur_node.right.data = cur_node.data
                print("  Splitting prefix: " + str(cur_node.prefix) + " into prefixes: " + str(cur_node.left.prefix) + ", " + str(cur_node.right.prefix) + " with data \"" + str(cur_node.data) + "\"")
                cur_node.data = ""
            else:
                if cur_node.left is not None:
                    queue.append(cur_node.left)
                if cur_node.right is not None:
                    queue.append(cur_node.right)

    def aggregate_data(self):
        root = self
        if root is None:
            return
        self.aggregate_data2(root)
        
    def aggregate_data2(self, node):
        if node is None:
            return
        self.aggregate_data2(node.left)
        if ((node.left is not None) and (node.right is not None)):
            if ((node.left.data != "") and (node.left.data == node.right.data) and (node.data == "")):
                node.data = node.left.data
                print("  Combining prefixes: "  + str(node.left.prefix) + ", " + str(node.right.prefix) + " into prefix: " + str(node.prefix) + " with data \"" + str(node.data) + "\"")
                node.left.data = ""
                node.right.data = ""
        self.aggregate_data2(node.right)

    def export_all_prefixes(self):
        root = self
        if root is None:
            return
        output = []

        def export_all_prefixes2(node):
            if node is None:
                return
            export_all_prefixes2(node.left)
            if node.data != "":
                output.append([node.prefix, "{:032b}".format(node.address), node.netmask, node.data])
            export_all_prefixes2(node.right)

        export_all_prefixes2(root)
        return output
    


if (len(sys.argv) <= 1 or (sys.argv[1] == "help") or (sys.argv[1] == "?") or (sys.argv[1] == "h") or (sys.argv[1] == "--help") or (sys.argv[1] == "-h")):
    print_help()
    sys.exit()

if len(sys.argv) != 3 and len(sys.argv) != 5:
    print('Incorrect number of arguments!')
    print_help()
    sys.exit()

# Get locations
locations = {}
if len(sys.argv) == 5:
    if sys.argv[3] == '-city' or sys.argv[3] == '-country':
        input_locatoins_file_path = sys.argv[4]
        if (os.path.isfile(input_locatoins_file_path) and (input_locatoins_file_path.endswith(".csv") or input_locatoins_file_path.endswith(".txt"))):
            locations = parse_locations(input_locatoins_file_path, sys.argv[3] == '-city')
        else:
            print('Error: specified file is not recognized csv/txt file, please specify another file. Supported extensions are csv/txt.\r\n')
            print_help()
            sys.exit()
    else:
        print('Error: Wrong option!\r\n')
        print_help()
        sys.exit()

# Open first geobase
input_first_file_path = sys.argv[1]
if (os.path.isfile(input_first_file_path) and (input_first_file_path.endswith(".csv") or input_first_file_path.endswith(".txt"))):
    data_first = check_geolite2_prefixes_func(input_first_file_path)
    if (len(data_first[2]) == 0):
        print("Input file contains no geo-data, exiting.")
        sys.exit()
    if data_first[0] > 0:
        if not re.match(r'^ *(Y|y)(E|e)(S|s) *$',input("Input file contains errors, type \"yes\" if you sure you want to recombine it anyways [No]: ")):
            print("Aborting action.")
            sys.exit()
    ipv4_prefix_root = BinaryTree("0.0.0.0/0", "")
    for line in data_first[2]:
        ipv4_prefix_root.set_prefix_data(re.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", line, maxsplit=1)[0], re.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", line, maxsplit=1)[1])
else:
    print("Error: specified file is not recognized csv/txt file, please specify another file. Supported extensions are csv/txt.\r\n")
    print_help()
    sys.exit()


# Open second geobase
input_second_file_path = sys.argv[2]
if (os.path.isfile(input_second_file_path) and (input_second_file_path.endswith(".csv") or input_second_file_path.endswith(".txt"))):
    data_second = check_geolite2_prefixes_func(input_second_file_path)
    if (len(data_second[2]) == 0):
        print("Input file contains no geo-data, exiting.")
        sys.exit()
    if data_second[0] > 0:
        if not re.match(r'^ *(Y|y)(E|e)(S|s) *$',input("Input file contains errors, type \"yes\" if you sure you want to recombine it anyways [No]: ")):
            print("Aborting action.")
            sys.exit()
else:
    print("Error: specified file is not recognized csv/txt file, please specify another file. Supported extensions are csv/txt.\r\n")
    print_help()
    sys.exit()


with io.open('cmp_result.log', 'w', encoding='utf-8') as file:
    for line in data_second[2]:
        prefix = re.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", line, maxsplit=1)[0]
        geo_mark = re.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", line, maxsplit=1)[1].split(',')[0]
        first_geobase_lookup = ipv4_prefix_root.get_prefix_data2(prefix)
        for lookup in first_geobase_lookup:
            if geo_mark == lookup[3].split(',')[0]:
                print(prefix, geo_mark, '- OK!')
            else:
                print(prefix, geo_mark, f'- NOT OK {lookup[0]} {lookup[3].split(",")[0]}!')
                geoname_1 = ''
                geoname_2 = ''
                if len(sys.argv) == 5 and lookup[3].split(",")[0] in locations.keys():
                    geoname_1 = ' ' + locations[lookup[3].split(",")[0]]
                if len(sys.argv) == 5 and geo_mark in locations.keys():
                    geoname_2 = ' ' + locations[geo_mark]
                    
                file.write(f'[Error] prefix: {lookup[0]}, geoname_id_1: {lookup[3].split(",")[0]}{geoname_1}, geoname_id_2: {geo_mark}{geoname_2}\n')
    print('The comparison result is written to a file cmp_result.log')
