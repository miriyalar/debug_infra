class SomeUtils:
    def merge_dict(self, d1, d2):
        for k,v2 in d2.items():
            v1 = d1.get(k) 
            if (isinstance(v1, dict) and
                isinstance(v2, dict) ):
                self.merge_dict(v1, v2)
            else:
                d1[k] = v2

    def merge_dict_v2(self, d1, d2):
        for k,v2 in d2.items():
            v1 = d1.get(k) 
            if (isinstance(v1, dict) and
                isinstance(v2, dict) ):
                self.merge_dict(v1, v2)
            elif isinstance(v1, list):
                if isinstance(v2, list):
                    v1.extend(v2)
                else:
                    v1.append(v2)
            else:
                d1[k] = v2


config = {}
config['1'] = [{'a1':'a1'}, {'b1':'b1'}]
config['3'] = 'c3'
config['4'] = 'c4'

x = {}
#x['1'] = [{'x1': 'x1'}, {'y1':'y1'}]
#x['2'] = [{'x2': 'x2'}, {'y2':'y2'}]
#x['3'] = 'x3'
#x['5'] = 'x5'

a = SomeUtils() 
import pdb; pdb.set_trace()
a.merge_dict_v2(config, x)
print config
