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

