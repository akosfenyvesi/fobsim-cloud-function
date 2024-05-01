import json

def filter_and_save(json_string):
    desired_keys = [
    "NumOfFogNodes",
    "num_of_users_per_fog_node",
    "NumOfTaskPerUser",
    "NumOfMiners",
    "number_of_each_miner_neighbours",
    "numOfTXperBlock",
    "puzzle_difficulty",
    "poet_block_time",
    "Max_enduser_payment",
    "miners_initial_wallet_value",
    "mining_award",
    "delay_between_fog_nodes",
    "delay_between_end_users",
    "Gossip_Activated",
    "Automatic_PoA_miners_authorization?",
    "Parallel_PoW_mining?",
    "Asymmetric_key_length",
    "Num_of_DPoS_delegates",
    "STOR_PLC(0=in the Fog,1=in the BC)"
    ]

    settings_dict = json.loads(json_string)

    filtered_settings = {key: settings_dict[key] for key in desired_keys}
    print(filtered_settings)
    with open('./Sim_parameters.json', 'w') as f:
        json.dump(filtered_settings, f, indent=4)

    return settings_dict

def modify_json_value(key_to_modify, new_value):
    with open('./Sim_parameters.json', 'r') as file:
        data = json.load(file)

    data[key_to_modify] = new_value

    with open('./Sim_parameters.json', 'w') as file:
        json.dump(data, file, indent=4)