import os

class Utils():
    def convert_unicode():
        def convert_unicode(input):
            if isinstance(input, dict):
                return {convert_unicode(key): convert_unicode(value) for key, value in input.iteritems()}
            elif isinstance(input, list):
                return [convert_unicode(element) for element in input]
            elif isinstance(input, unicode):
                return input.encode('utf-8')
            else:
                return input
        # end convert_unicode(input)
                                                         
        return convert_unicode
    convert_unicode = staticmethod(convert_unicode())

    @staticmethod
    def merge_dict(d1, d2):
        if not d2:
            return d1
        for k,v2 in d2.items():
            v1 = d1.get(k) 
            if (isinstance(v1, dict) and
                isinstance(v2, dict) ):
                Utils.merge_dict(v1, v2)
            elif isinstance(v1, list):
                if isinstance(v2, list):
                    v1.extend(v2)
                else:
                    v1.append(v2)
            else:
                d1[k] = v2


    @staticmethod
    def dict_to_filesystem(d, cur_path='./', console=False):
        if isinstance(d, dict):
            for k, v in d.items():
                v = d.get(k)
                path = os.path.join(cur_path, k)
                if isinstance(v, dict) or isinstance(v, list):
                    if not os.path.exists(path):
                        os.makedirs(path)
                    if console:
                        print path
                    Utils.dict_to_filesystem(v, path)
                else:
                    input_file = open(path, 'a')
                    input_file.write(str(v))
                    input_file.close()
                    if console:
                        print path, v
        elif isinstance(d, list):
            for i, v in enumerate(d):
                path = os.path.join(cur_path, str(i))
                if isinstance(v, dict) or isinstance(v, list):
                    if not os.path.exists(path):
                        os.makedirs(path)
                    if console:
                        print path
                    Utils.dict_to_filesystem(v, path)
                else:
                    input_file = open(path, 'a')
                    input_file.write(str(v))
                    input_file.close()
                    if console:
                        print ' ' + v
        else:
            input_file = open(cur_path, 'a')
            input_file.write(str(d))
            input_file.close()
            if console:
                print cur_path, d

