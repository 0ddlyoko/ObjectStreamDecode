import struct

from io import BytesIO


class Constants:
    STREAM_MAGIC = 0xACED
    STREAM_VERSION = 5

    MAX_BLOCK_SIZE = 1024

    # First tag value
    TC_BASE = 0x70
    # Null object reference
    TC_NULL = 0x70
    # Reference to an object already written into the stream
    TC_REFERENCE = 0x71
    # new Class Descriptor
    TC_CLASSDESC = 0x72
    # new Object
    TC_OBJECT = 0x73
    # new String
    TC_STRING = 0x74
    # new Array
    TC_ARRAY = 0x75
    # Reference to Class
    TC_CLASS = 0x76
    # Block of optional data. Byte following tag indicates number of bytes in this block data.
    TC_BLOCKDATA = 0x77
    # End of optional block data blocks for an object.
    TC_ENDBLOCKDATA = 0x78
    # Reset stream context. All handles written into stream are reset.
    TC_RESET = 0x79
    # long Block data. The long following the tag indicates the number of bytes in this block data.
    TC_BLOCKDATALONG = 0x7A
    # Exception during write
    TC_EXCEPTION = 0x7B
    # Long string
    TC_LONGSTRING = 0x7C
    # new Proxy Class Descriptor
    TC_PROXYCLASSDESC = 0x7D
    # new Enum constant
    TC_ENUM = 0x7E

    # Bit mask for ObjectStreamClass flag. Indicates a Serializable class defines its own writeObject method.
    SC_WRITE_METHOD = 0x01
    # Bit mask for ObjectStreamClass flag. Indicates class is Serializable.
    SC_SERIALIZABLE = 0x02
    # Bit mask for ObjectStreamClass flag. Indicates class is Externalizable.
    SC_EXTERNALIZABLE = 0x04
    # Bit mask for ObjectStreamClass flag. Indicates Externalizable data written in Block Data mode. Added for PROTOCOL_VERSION_2.
    SC_BLOCK_DATA = 0x08
    # Bit mask for ObjectStreamClass flag. Indicates class is an enum type.
    SC_ENUM = 0x10

    # Support Python 3
    PRIMITIVE_TYPES = {
        'B': 'byte',
        'C': 'char',
        'D': 'double',
        'F': 'float',
        'I': 'int',
        'J': 'long',
        'S': 'short',
        'Z': 'boolean',
        # Support Python 3
        b'B': 'byte',
        b'C': 'char',
        b'D': 'double',
        b'F': 'float',
        b'I': 'int',
        b'J': 'long',
        b'S': 'short',
        b'Z': 'boolean',
        ord('B'): 'byte',
        ord('C'): 'char',
        ord('D'): 'double',
        ord('F'): 'float',
        ord('I'): 'int',
        ord('J'): 'long',
        ord('S'): 'short',
        ord('Z'): 'boolean',
    }
    OBJECT_TYPES = {
        '[': 'array',
        'L': 'object',
        # Support Python 3
        b'[': 'array',
        b'L': 'object',
        ord('['): 'array',
        ord('L'): 'object',
    }
    TYPES = {}
    TYPES.update(PRIMITIVE_TYPES)
    TYPES.update(OBJECT_TYPES)
    BASE_WIRE_HANDLE = 0x7E0000


class Handler:
    def __init__(self, io):
        self.io = io
        self.pos = 0
        self.end = 0
        self.block_mode = False
        self.block_data = None
        self.references = []
        # Check header
        self.header = Header()
        self.header.decode(self)
        # self.set_block_data_mode(True)

    def set_block_data_mode(self, newmode):
        if newmode == self.block_mode:
            return
        if newmode:
            self.pos = 0
            self.end = 0
        elif self.pos < self.end:
            raise Exception("unread block data")
        self.block_mode = newmode
        return not self.block_mode

    def get_unread(self):
        return self.end - self.pos

    def skip(self, n):
        while n > 0:
            skip = self.io.seek(n, 1)
            if skip == 0:
                raise EOFError("Unexpected end of stream")
            n -= skip

    def refill(self):
        if not self.block_mode:
            raise Exception("Refilling disabled")
        # Skip unread block data elements
        self.skip(self.get_unread())
        self.set_block_data_mode(False)
        block_data = decode_object(self)
        self.set_block_data_mode(True)
        if block_data.__class__ not in [BlockData, BlockDataLong]:
            raise Exception(f"Invalid block data: {self.block_data}")
        self.block_data = block_data
        self.pos = 0
        self.end = self.block_data.size

    def read_struct(self, unpack):
        ln = struct.calcsize(unpack)
        if self.block_mode and self.pos == self.end:
            self.refill()
        if self.block_mode:
            # read in block data
            ba = self.block_data.io.read(ln)
        else:
            ba = self.io.read(ln)
        if len(ba) != ln:
            raise EOFError("Unexpected end of stream")
        self.pos += ln
        return struct.unpack(unpack, ba)

    def read_boolean(self):
        (value,) = self.read_struct(">?")
        return value

    def read_byte(self):
        (value,) = self.read_struct(">B")
        return value

    def read_char(self):
        (value,) = self.read_struct(">ss")
        return value

    def read_double(self):
        (value,) = self.read_struct(">D")
        return value

    def read_float(self):
        (value,) = self.read_struct(">F")
        return value

    def read_short(self):
        # We can't use _read_struct(">H") because the 2 bytes could be split in 2 blocks
        v1 = self.read_byte()
        v2 = self.read_byte()
        return (v1 << 8) + v2

    def read_int(self):
        # We can't use _read_struct(">I") because the 4 bytes could be split in 2 blocks
        v1 = self.read_short()
        v2 = self.read_short()
        return (v1 << 16) + v2

    def read_long(self):
        # We can't use _read_struct(">Q") because the 8 bytes could be split in 2 blocks
        v1 = self.read_int()
        v2 = self.read_int()
        return (v1 << 32) + v2

    def read_primitive(self, primitive_type):
        if primitive_type == 'byte':
            return self.read_byte()
        if primitive_type == 'char':
            return self.read_char()
        if primitive_type == 'double':
            return self.read_double()
        if primitive_type == 'float':
            return self.read_float()
        if primitive_type == 'int':
            return self.read_int()
        if primitive_type == 'long':
            return self.read_long()
        if primitive_type == 'short':
            return self.read_short()
        if primitive_type == 'boolean':
            return self.read_boolean()
        return decode_object(self)

    def read_object(self):
        return decode_object(self)

    def add_reference(self, reference):
        self.references.append(reference)

    def get_reference(self, reference):
        return self.references[reference]


class Element:

    def decode(self, handler: Handler):
        return self

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__str__()


class BlockData(Element):
    def __init__(self):
        self.size = 0
        self.content = ""
        self.io = None

    def decode(self, handler: Handler):
        self.size = self.read_size(handler)
        if self.size == 0:
            return
        self.content = handler.io.read(self.size)
        if not self.content or len(self.content) != self.size:
            raise EOFError("Unexpected end of stream")
        self.io = BytesIO(self.content)

    def read_size(self, handler: Handler):
        return handler.read_byte()


class BlockDataLong(BlockData):
    def __init__(self):
        super().__init__()

    def read_size(self, handler: Handler):
        return handler.read_int()


class ClassDesc(Element):
    def __init__(self):
        self.content: Null | ProxyClassDesc | NewClassDesc = None

    def decode(self, handler: Handler):
        type = decode_object(handler)
        if type.__class__ not in [Null, Reference, ProxyClassDesc, NewClassDesc]:
            raise Exception(f"Invalid type for class desc: {type}")
        if type.__class__ is Reference:
            type = type.obj
        self.content = type

    def __str__(self):
        return f"ClassDesc({self.content})"


class EndBlockData(Element):
    def __init__(self):
        pass


class Enum(Element):
    def __init__(self):
        self.description = None
        self.name = None

    def decode(self, handler: Handler):
        self.description = ClassDesc()
        self.description.decode(handler)
        handler.add_reference(self)
        type = decode_object(handler)
        if type.__class__ not in [LongString, String, Reference]:
            raise Exception(f"Invalid type for enum: {type}")
        if type.__class__ is Reference:
            type = type.obj
        self.name = type.content

    def __str__(self):
        return f"Enum({self.name})"


class Field(Element):
    def __init__(self):
        self.code = 0
        self.type = 0
        self.field_name = None
        self.field_type = None

    def decode(self, handler: Handler):
        self.code = handler.read_byte()
        if not self.is_valid():
            raise Exception(f"Invalid type code: {self.code}")
        self.type = Constants.TYPES[self.code]
        class_name = String()
        class_name.decode(handler)
        self.field_name = class_name.content
        if self.is_object():
            type = decode_object(handler)
            if type.__class__ not in [String, Reference]:
                raise Exception(f"Invalid type for field: {type}")
            if type.__class__ is Reference:
                type = type.obj
            self.field_type = type

    def is_valid(self):
        return self.code in Constants.TYPES

    def is_object(self):
        return self.code in Constants.OBJECT_TYPES

    def is_primitive(self):
        return self.code in Constants.PRIMITIVE_TYPES

    def get_primitive_type(self):
        return Constants.PRIMITIVE_TYPES[self.code]

    def __str__(self):
        return f"Field({self.field_name})"


class Header(Element):
    def __init__(self):
        self.magic = Constants.STREAM_MAGIC
        self.version = Constants.STREAM_VERSION

    def decode(self, handler: Handler):
        (self.magic, self.version) = self._decode_magic(handler)

    def _decode_magic(self, handler: Handler):
        return handler.read_struct(">HH")


class JavaException(Element):
    def __init__(self):
        self.exception = None

    def decode(self, handler: Handler):
        exception = decode_object(handler)
        if exception.__class__ is Reference:
            exception = exception.obj
        self.exception = exception


class LongString(Element):
    def __init__(self):
        self.content = ""

    def decode(self, handler: Handler):
        ln = handler.read_long()
        if ln == 0:
            return
        contents = []
        for i in range(ln):
            contents.append(chr(handler.read_byte()))
        self.content = "".join(contents)


class NewArray(Element):
    def __init__(self):
        self.new_class_desc: NewClassDesc = None
        self.size = 0
        self.type = ""
        self.contents = []

    def decode(self, handler: Handler):
        class_desc = decode_object(handler)
        if class_desc.__class__ not in [NewClassDesc, Reference]:
            raise Exception(f"Invalid type for class desc: {class_desc}")
        if class_desc.__class__ is Reference:
            class_desc = class_desc.obj
        self.new_class_desc = class_desc
        handler.add_reference(self)
        self.type = self.array_type()
        self.size = handler.read_int()
        contents = []
        for i in range(self.size):
            content = handler.read_primitive(self.type)
            if content.__class__ is Reference:
                content = content.obj
            contents.append(content)
        self.contents = contents

    def array_type(self):
        if self.new_class_desc.__class__ is not NewClassDesc:
            return False
        class_name = self.new_class_desc.class_name
        if not class_name or class_name[0] not in Constants.OBJECT_TYPES or Constants.OBJECT_TYPES[class_name[0]] != 'array':
            return False
        decoded_type = class_name[1]
        if decoded_type in Constants.PRIMITIVE_TYPES:
            return Constants.PRIMITIVE_TYPES[decoded_type]
        if decoded_type == 'L':
            # Object
            return class_name[2:class_name.index(';')]
        raise Exception("Invalid array type")

    def __str__(self):
        return f"NewArray({self.type}, {self.size}, {self.contents})"


class NewClass(Element):
    def __init__(self):
        self.class_desc = None

    def decode(self, handler: Handler):
        self.class_desc = ClassDesc()
        self.class_desc.decode(handler)
        handler.add_reference(self)


class NewClassDesc(Element):
    def __init__(self):
        self.class_name = ""
        self.serial_version_uid = 0
        self.flags = 0
        self.fields = []
        self.super_class: ClassDesc = None

    def decode(self, handler: Handler):
        class_name = String()
        class_name.decode(handler)
        self.class_name = class_name.content
        self.serial_version_uid = handler.read_long()
        handler.add_reference(self)
        self.flags = handler.read_byte()
        fields_count = handler.read_short()
        fields = []
        for i in range(fields_count):
            field = Field()
            field.decode(handler)
            fields.append(field)
        self.fields = fields
        # TODO Check for Annotation
        # TODO Here it will fail as there is the TC_END_BLOCK_DATA tag which should be handled by the Annotation
        # TODO Check if there is a super function

        type = decode_object(handler)
        if type.__class__ not in [EndBlockData]:
            raise Exception(f"Invalid type for enum: {type}")

        self.super_class = ClassDesc()
        self.super_class.decode(handler)

    def __str__(self):
        return f"NewClassDesc({self.class_name})"


class NewObject(Element):
    def __init__(self):
        self.class_desc: ClassDesc = None
        self.contents = []

    def decode(self, handler: Handler):
        self.class_desc = ClassDesc()
        self.class_desc.decode(handler)
        handler.add_reference(self)
        self.contents = self.decode_class_data(handler, self.get_class_content(self.class_desc))

    def decode_class_data(self, handler: Handler, new_class_desc):
        if not new_class_desc:
            return []
        contents = []
        if new_class_desc.super_class:
            contents = self.decode_class_data(handler, self.get_class_content(new_class_desc.super_class))

        for field in new_class_desc.fields:
            if field.is_primitive():
                primitive_type = field.get_primitive_type()
                value = handler.read_primitive(primitive_type)
                contents.append(value)
            else:
                content = decode_object(handler)
                if content.__class__ is Reference:
                    content = content.obj
                contents.append(content)
        return contents

    def get_class_content(self, class_desc: ClassDesc):
        if not class_desc.content:
            return False
        if class_desc.content.__class__ is NewClassDesc:
            return class_desc.content
        return False

    def __str__(self):
        return f"NewObject(name={self.class_desc.content}, content={self.contents})"


class Null(Element):
    def __init__(self):
        pass


class ProxyClassDesc(Element):
    def __init__(self):
        self.ifaces = []
        self.super_class = None

    def decode(self, handler: Handler):
        handler.add_reference(self)
        size = handler.read_int()
        for i in range(size):
            iface = String()
            iface.decode(handler)
            self.ifaces.append(iface.content)
        # TODO Check for Annotation
        # TODO Here it will fail as there is the TC_END_BLOCK_DATA tag which should be handled by the Annotation
        # TODO Check if there is a super function

        type = decode_object(handler)
        if type.__class__ not in [EndBlockData]:
            raise Exception(f"Invalid type for enum: {type}")

        self.super_class = ClassDesc()
        self.super_class.decode(handler)


class Reference(Element):
    def __init__(self):
        self.ref = 0
        self.obj = None

    def decode(self, handler: Handler):
        self.ref = handler.read_int() - Constants.BASE_WIRE_HANDLE
        self.obj = handler.get_reference(self.ref)

    def __str__(self):
        return f"Reference({self.ref})"


class String(Element):
    def __init__(self):
        self.content = ""

    def decode(self, handler: Handler):
        ln = handler.read_short()
        if ln == 0:
            return
        contents = []
        for i in range(ln):
            contents.append(chr(handler.read_byte()))
        self.content = "".join(contents)

    def __str__(self):
        return f"String({self.content})"


def decode_object(handler: Handler):
    tc = handler.read_byte()
    if not tc:
        raise Exception("Invalid type code")
    if tc == Constants.TC_ARRAY:
        new_array = NewArray()
        new_array.decode(handler)
        return new_array
    if tc == Constants.TC_BLOCKDATA:
        new_block_data = BlockData()
        new_block_data.decode(handler)
        return new_block_data
    if tc == Constants.TC_BLOCKDATALONG:
        new_block_data_long = BlockDataLong()
        new_block_data_long.decode(handler)
        return new_block_data_long
    if tc == Constants.TC_CLASS:
        new_class = NewClass()
        new_class.decode(handler)
        return new_class
    if tc == Constants.TC_CLASSDESC:
        new_class_desc = NewClassDesc()
        new_class_desc.decode(handler)
        return new_class_desc
    if tc == Constants.TC_ENDBLOCKDATA:
        return EndBlockData()
    if tc == Constants.TC_ENUM:
        new_enum = Enum()
        new_enum.decode(handler)
        return new_enum
    if tc == Constants.TC_EXCEPTION:
        new_exception = JavaException()
        new_exception.decode(handler)
        return new_exception
    if tc == Constants.TC_LONGSTRING:
        new_long_string = LongString()
        new_long_string.decode(handler)
        handler.add_reference(new_long_string)
        return new_long_string
    if tc == Constants.TC_NULL:
        return Null()
    if tc == Constants.TC_OBJECT:
        new_object = NewObject()
        new_object.decode(handler)
        return new_object
    if tc == Constants.TC_PROXYCLASSDESC:
        raise Exception("TC_PROXYCLASSDESC not supported")
    if tc == Constants.TC_REFERENCE:
        new_reference = Reference()
        new_reference.decode(handler)
        return new_reference
    if tc == Constants.TC_STRING:
        new_string = String()
        new_string.decode(handler)
        handler.add_reference(new_string)
        return new_string
    pass
