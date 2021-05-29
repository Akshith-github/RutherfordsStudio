
####################################  short definations  #######################
def servent_shortdef_extractor(json_dict_elem):
    meanings=["No meanings found"]
    if(json_dict_elem.get('shortdef')):
        return json_dict_elem.get('shortdef')
    return meanings

def shortdef_extract(json_):
    if(type(json_)==list):
        meanings=[]
        for i in range(len(json_)):
            meanings.append(servent_shortdef_extractor(json_[i]))
    elif(type(json_)==dict):
        meanings=[servent_shortdef_extractor(json_)]
    else:
        return ['No meanings']
    return meanings

####################################  {fl} part of speech of word  #######################
def servent_fl_extractor(json_dict_elem):
    pos="unknown"
    if(json_dict_elem.get('fl')):
        return json_dict_elem.get('fl')
    return pos

def fl_extract(json_):
    if(type(json_)==list):
        poss=[]
        for i in range(len(json_)):
            poss.append(servent_fl_extractor(json_[i]))
    elif(type(json_)==dict):
        poss=[servent_fl_extractor(json_)]
    else:
        return []
    return poss

####################################  stems and isoffensive of word  #######################
def servent_meta_extractor(json_dict_elem):
    s="None";o="unknown"
    if(json_dict_elem.get('meta')):
        if(json_dict_elem.get('meta').get('stems')):
            s=json_dict_elem.get('meta').get('stems')
        if('offensive' in json_dict_elem.get('meta')):
            o=[json_dict_elem.get('meta').get('offensive')]
    return s,o

def meta_extract(json_):
    if(type(json_)==list):
        stems=[]
        offensives=[]
        for i in range(len(json_)):
            s,o=servent_meta_extractor(json_[i])
            stems.append(s)
            offensives.append(o)
    elif(type(json_)==dict):
        stems,offensives=servent_meta_extractor(json_)
    else:
        return [],[]
    return stems,offensives

####################################  similar words and pos #######################
def servent_uros_extractor(json_dict_elem):
    ure=[];poss=[]
    uros_i=json_dict_elem.get('uros') if(json_dict_elem.get('uros')) else []
    for i in range(len(uros_i)):
        if(uros_i[i].get('ure')):
            ure.append(uros_i[i].get('ure'))
        if(uros_i[i].get('fl')):
            poss.append(uros_i[i].get('fl'))
    return ure,poss
    
def uros_extract(json_):
    if(type(json_)==list):
        ure=[];poss=[]
        for i in range(len(json_)):
            u,p=servent_uros_extractor(json_[i]);
            ure.extend(u);poss.extend(p)
    elif(type(json_)==dict):
        ure,poss=servent_uros_extractor(json_)
    else:   return [],[]
    return ure,poss

###################################  definations fl examples dt ###############################

def servent_defs_extractor(json_dict_elem):
    import re
    defst=[];vd=[];examples=[];
    defs=json_dict_elem.get('def') if(json_dict_elem.get('def')) else []
    for i in range(len(defs)):
        if(defs[i].get('vd')):   vd.append(defs[i].get('vd'))
        else: vd.append(defs[i].get('Unknown'))
        defst_i=[]
        if(defs[i].get('sseq')):   
            sseq=defs[i].get('sseq')
            for i in range(len(sseq)):
                in_sseq=sseq[i]
                for j in range(len(in_sseq)):
                    try:
                        defst_i.append(in_sseq[j][1]['dt'][0][1])
                    except:
                        defst_i.append('Unknown')
        defst.append(defst_i)
        try:
            if(len(re.findall("'t': '([^']*)'",str(defs[i])))>=1 ):
                temp=re.findall("'t': '([^']*)'",str(defs[i]))
                for i in range(len(temp)):
                    while('{' in temp[i]):
                        st=temp[i].index('{');end=temp[i].index('}')
                        temp[i] = temp[i][:st]+temp[i][end+1:]
                if(temp):
                    examples.extend(temp)
        except:
            pass
    return defst,vd,examples
# for i in range(len(b[0]['def'])):
#     # print( str(b[0]['def'][i]) )
#     if(re.findall("'t': '([^']*)'",str(b[0]['def'][i])) ):
#         print(re.findall("'t': '([^']*)'",str(b[0]['def'][i])))

def def_extract(json_):
    if(type(json_)==list):
        defs=[];vd=[];examples=[]
        for i in range(len(json_)): 
            d,v,e=servent_defs_extractor(json_[i]);
            defs.append(d);vd.append(v);examples.append(e)
    elif(type(json_)==dict):    
        defs,vd,examples=servent_defs_extractor(json_)
    else:   return [],[],[]
    return defs,vd,examples