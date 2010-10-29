# This file is part of Androguard.
#
# Copyright (C) 2010, Anthony Desnos <desnos at t0t0.org>
# All rights reserved.
#
# Androguard is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Androguard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of  
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Androguard.  If not, see <http://www.gnu.org/licenses/>.

import bytecode

from bytecode import SV, SVs

from struct import pack, unpack, calcsize
from collections import namedtuple
import re

# Special functions to manage more easily special arguments of bytecode 
def special_F0(x) :
   return [ i for i in x ]

def special_F0R(x) :
   return [ x ]

def special_F1(x) :
   return (x[0] << 8) | x[1]

def special_F1R(x) :
   return [ (x & 0xFF00) >> 8, x & 0x00FF ]

def special_F2(x) :
   v = ((x[0] << 8) | x[1])
   if v > 0x7FFF :
      v = (0x7FFF & v) - 0x8000

   return v

def special_F2R(x) :
   val = x & 0xFFFF
   return [ (val & 0xFF00) >> 8, val & 0x00FF ]

def special_F3(x) :
   val = (x[0] << 24) | (x[1] << 16) | (x[2] << 8) | x[3]
   if val > 0x7fffffff :
      val = (0x7fffffff & val) - 0x80000000
   return val

def special_F3R(x) :
   val = x & 0xFFFFFFFF
   return [ (val & 0xFF000000) >> 24, (val & 0x00FF0000) >> 16, (val & 0x0000FF00) >> 8, val & 0x000000FF ]

# The list of java bytecodes, with their value, name, and special functions !
JAVA_OPCODES = {
                  0x32 : [ "aaload" ],
                  0x53 : [ "aastore" ],
                  0x1  : [ "aconst_null" ],
                  0x19 : [ "aload", "index:B", special_F0, special_F0, None ],
                  0x2a : [ "aload_0" ],
                  0x2b : [ "aload_1" ],
                  0x2c : [ "aload_2" ],
                  0x2d : [ "aload_3" ],
                  0xbd : [ "anewarray", "indexbyte1:B indexbyte2:B", special_F1, special_F1R, "get_class" ],
                  0xb0 : [ "areturn" ],
                  0xbe : [ "arraylength" ],
                  0x3a : [ "astore", "index:B", special_F0, special_F0, None ],
                  0x4b : [ "astore_0" ],
                  0x4c : [ "astore_1" ],
                  0x4d : [ "astore_2" ],
                  0x4e : [ "astore_3" ],
                  0xbf : [ "athrow" ],
                  0x33 : [ "baload" ],
                  0x54 : [ "bastore" ],
                  0x10 : [ "bipush", "byte:B", special_F0, special_F0R, None ],
                  0x34 : [ "caload" ],
                  0x55 : [ "castore" ],
                  0xc0 : [ "checkcast", "indexbyte1:B indexbyte2:B" ],
                  0x90 : [ "d2f" ],
                  0x8e : [ "d2i" ],
                  0x8f : [ "d2l" ],
                  0x63 : [ "dadd" ],
                  0x31 : [ "daload" ],
                  0x52 : [ "dastore" ],
                  0x98 : [ "dcmpg" ],
                  0x97 : [ "dcmpl" ],
                  0xe  : [ "dconst_0" ],
                  0xf  : [ "dconst_1" ],
                  0x6f : [ "ddiv" ],
                  0x18 : [ "dload", "index:1" ],
                  0x26 : [ "dload_0" ],
                  0x27 : [ "dload_1" ],
                  0x28 : [ "dload_2" ],
                  0x29 : [ "dload_3" ],
                  0x6b : [ "dmul" ],
                  0x77 : [ "dneg" ],
                  0x73 : [ "drem" ],
                  0xaf : [ "dreturn" ],
                  0x39 : [ "dstore", "index:B", special_F0, special_F0, None ],
                  0x47 : [ "dstore_0" ],
                  0x48 : [ "dstore_1" ],
                  0x49 : [ "dstore_2" ],
                  0x4a : [ "dstore_3" ],
                  0x67 : [ "dsub" ],
                  0x59 : [ "dup" ],
                  0x5a : [ "dup_x1" ],
                  0x5b : [ "dup_x2" ],
                  0x5c : [ "dup2" ],
                  0x5d : [ "dup2_x1" ],
                  0x5e : [ "dup2_x2" ],
                  0x8d : [ "f2d" ],
                  0x8b : [ "f2i" ],
                  0x8c : [ "f2l" ],
                  0x62 : [ "fadd" ],
                  0x30 : [ "faload" ],
                  0x51 : [ "fastore" ],
                  0x96 : [ "fcmpg" ],
                  0x95 : [ "fcmpl" ],
                  0xb  : [ "fconst_0" ],
                  0xc  : [ "fconst_1" ],
                  0xd  : [ "fconst_2" ],
                  0x6e : [ "fdiv" ],
                  0x17 : [ "fload", "index:B", special_F0, special_F0, None ],
                  0x22 : [ "fload_0" ],
                  0x23 : [ "fload_1" ],
                  0x24 : [ "fload_2" ],
                  0x25 : [ "fload_3" ],
                  0x6a : [ "fmul" ],
                  0x76 : [ "fneg" ],
                  0x72 : [ "frem" ],
                  0xae : [ "freturn" ],
                  0x38 : [ "fstore", "index:B", special_F0, special_F0, None ],
                  0x43 : [ "fstore_0" ],
                  0x44 : [ "fstore_1" ],
                  0x45 : [ "fstore_2" ],
                  0x46 : [ "fstore_3" ],
                  0x66 : [ "fsub" ],
                  0xb4 : [ "getfield", "indexbyte1:B indexbyte2:B", special_F1, special_F1R, "get_field" ],
                  0xb2 : [ "getstatic", "indexbyte1:B indexbyte2:B", special_F1, special_F1R, "get_field", "get_field_index" ],
                  0xa7 : [ "goto", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0xc8 : [ "goto_w", "branchbyte1:B branchbyte2:B branchbyte3:B branchbyte4:B" ],
                  0x91 : [ "i2b" ],
                  0x92 : [ "i2c" ],
                  0x87 : [ "i2d" ],
                  0x86 : [ "i2f" ],
                  0x85 : [ "i2l" ],
                  0x93 : [ "i2s" ],
                  0x60 : [ "iadd" ],
                  0x2e : [ "iaload" ],
                  0x7e : [ "iand" ],
                  0x4f : [ "iastore" ],
                  0x2  : [ "iconst_m1" ],
                  0x3  : [ "iconst_0" ],
                  0x4  : [ "iconst_1" ],
                  0x5  : [ "iconst_2" ],
                  0x6  : [ "iconst_3" ],
                  0x7  : [ "iconst_4" ],
                  0x8  : [ "iconst_5" ],
                  0x6c : [ "idiv" ],
                  0xa5 : [ "if_acmpeq", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0xa6 : [ "if_acmpne", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0x9f : [ "if_icmpeq", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0xa0 : [ "if_icmpne", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0xa1 : [ "if_icmplt", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0xa2 : [ "if_icmpge", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0xa3 : [ "if_icmpgt", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0xa4 : [ "if_icmple", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0x99 : [ "ifeq", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0x9a : [ "ifne", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0x9b : [ "iflt", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0x9c : [ "ifge", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0x9d : [ "ifgt", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0x9e : [ "ifle", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0xc7 : [ "ifnonnull", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0xc6 : [ "ifnull", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0x84 : [ "iinc", "index:B const:B", special_F0, special_F0, None ],
                  0x15 : [ "iload", "index:B", special_F0, special_F0, None ],
                  0x1a : [ "iload_0" ],
                  0x1b : [ "iload_1" ],
                  0x1c : [ "iload_2" ],
                  0x1d : [ "iload_3" ],
                  0x68 : [ "imul" ],
                  0x74 : [ "ineg" ], 
                  0xc1 : [ "instanceof", "indexbyte1:B indexbyte2:B" ],
                  0xb9 : [ "invokeinterface", "indexbyte1:B indexbyte2:B count:B null:B" ],
                  0xb7 : [ "invokespecial", "indexbyte1:B indexbyte2:B", special_F1, special_F1R, "get_method", "get_method_index" ],
                  0xb8 : [ "invokestatic", "indexbyte1:B indexbyte2:B", special_F1, special_F1R, "get_method", "get_method_index" ],
                  0xb6 : [ "invokevirtual", "indexbyte1:B indexbyte2:B", special_F1, special_F1R, "get_method", "get_method_index" ],
                  0x80 : [ "ior" ],
                  0x70 : [ "irem" ],
                  0xac : [ "ireturn" ],
                  0x78 : [ "ishl" ],
                  0x7a : [ "ishr" ],
                  0x36 : [ "istore", "index:B", special_F0, special_F0, None ],
                  0x3b : [ "istore_0" ],
                  0x3c : [ "istore_1" ],
                  0x3d : [ "istore_2" ],
                  0x3e : [ "istore_3" ],
                  0x64 : [ "isub" ],
                  0x7c : [ "iushr" ],
                  0x82 : [ "ixor" ],
                  0xa8 : [ "jsr", "branchbyte1:B branchbyte2:B", special_F2, special_F2R, None ],
                  0xc9 : [ "jsr_w", "branchbyte1:B branchbyte2:B branchbyte3:B branchbyte4:B", special_F3, special_F3R, None ],
                  0x8a : [ "l2d" ],
                  0x89 : [ "l2f" ],
                  0x88 : [ "l2i" ],
                  0x61 : [ "ladd" ],
                  0x2f : [ "laload" ],
                  0x7f : [ "land" ],
                  0x50 : [ "lastore" ],
                  0x94 : [ "lcmp" ],
                  0x9  : [ "lconst_0" ],
                  0xa  : [ "lconst_1" ],
                  0x12 : [ "ldc", "index:B", special_F0, special_F0R, "get_value" ],
                  0x13 : [ "ldc_w", "indexbyte1:B indexbyte2:B", special_F2, special_F2R, None ],
                  0x14 : [ "ldc2_w", "indexbyte1:B indexbyte2:B", special_F2, special_F2R, None ],
                  0x6d : [ "ldiv" ],
                  0x16 : [ "lload", "index:B", special_F0, special_F0, None ],
                  0x1e : [ "lload_0" ],
                  0x1f : [ "lload_1" ],
                  0x20 : [ "lload_2" ],
                  0x21 : [ "lload_3" ],
                  0x69 : [ "lmul" ],
                  0x75 : [ "lneg" ],
                  0xab : [ "lookupswitch", "bytepad1:B bytepad2:B bytepad3:B defaultbyte1:B defaultbyte2:B defaultbyte2:B defaultbyte3:B defaultbyte4:B npairs1:B npairs2:B npairs3:B npairs4:B" ], # TODO
                  0x81 : [ "lor" ],
                  0x71 : [ "lrem" ],
                  0xad : [ "lreturn" ],
                  0x79 : [ "lshl" ],
                  0x7b : [ "lshr" ],
                  0x37 : [ "lstore", "index:B", special_F0, special_F0, None ],
                  0x3f : [ "lstore_0" ],
                  0x40 : [ "lstore_1" ],
                  0x41 : [ "lstore_2" ],
                  0x42 : [ "lstore_3" ],
                  0x65 : [ "lsub" ],
                  0x7d : [ "lushr" ],
                  0x83 : [ "lxor" ],
                  0xc2 : [ "monitorenter" ],
                  0xc3 : [ "monitorexit" ],
                  0xc5 : [ "multianewarray", "indexbyte1:B indexbyte2:B dimensions:B" ],
                  0xbb : [ "new", "indexbyte1:B indexbyte2:B", special_F1, special_F1R, "get_class" ],
                  0xbc : [ "newarray", "atype:B", special_F0, special_F0, "get_array_type" ],
                  0x0  : [ "nop" ],
                  0x57 : [ "pop" ],
                  0x58 : [ "pop2" ],
                  0xb5 : [ "putfield", "indexbyte1:B indexbyte2:B", special_F1, special_F1R, "get_field" ],
                  0xb3 : [ "putstatic", "indexbyte1:B indexbyte2:B" ],
                  0xa9 : [ "ret", "index:B", special_F0, special_F0, None ],
                  0xb1 : [ "return" ],
                  0x35 : [ "saload" ],
                  0x56 : [ "sastore" ],
                  0x11 : [ "sipush", "byte1:B byte2:B", special_F1, special_F1R, None ],
                  0x5f : [ "swap" ],
                  0xaa : [ "tableswitch" ], # FIXME
                  0xc4 : [ "wide" ], # FIXME
               }

# Invert the value and the name of the bytecode
INVERT_JAVA_OPCODES = dict([( JAVA_OPCODES[k][0], k ) for k in JAVA_OPCODES]) 

# List of java bytecodes which can modify the control flow
BRANCH_JAVA_OPCODES = [ "goto", "goto_w", "if_acmpeq", "if_icmpeq", "if_icmpne", "if_icmplt", "if_icmpge", "if_icmpgt", "if_icmple", "ifeq", "ifne", "iflt", "ifge", "ifgt", "ifle", "ifnonnull", "ifnull", "jsr", "jsr_w" ]

INTEGER_INSTRUCTIONS = [ "bipush", "sipush" ]

def EXTRACT_INFORMATION(op_value) :
   """Extract information (special functions) about a bytecode"""
   r_function = JAVA_OPCODES[ op_value ][2]      
   v_function = JAVA_OPCODES[ op_value ][3]                                             
   f_function = JAVA_OPCODES[ op_value ][4]
   
   r_format = ">"      
   r_buff = [] 

   format = JAVA_OPCODES[ op_value ][1]      
   l = format.split(" ")
   for j in l :         
      operands = j.split(":")

      name = operands[0] + " "
      val = operands[1]
      
      r_buff.append( name.replace(' ', '') )
      r_format += val

   return ( r_function, v_function, r_buff, r_format, f_function )


METHOD_INFO             =       [ '>HHHH',      namedtuple("MethodInfo", "access_flags name_index descriptor_index attributes_count") ]
ATTRIBUTE_INFO          =       [ '>HL',        namedtuple("AttributeInfo", "attribute_name_index attribute_length") ]
FIELD_INFO              =       [ '>HHHH',      namedtuple("FieldInfo", "access_flags name_index descriptor_index attributes_count") ]
LINE_NUMBER_TABLE       =       [ '>HH',        namedtuple("LineNumberTable", "start_pc line_number") ]
EXCEPTION_TABLE         =       [ '>HHHH',      namedtuple("ExceptionTable", "start_pc end_pc handler_pc catch_type") ]
LOCAL_VARIABLE_TABLE    =       [ '>HHHHH',     namedtuple("LocalVariableTable", "start_pc length name_index descriptor_index index") ]

CODE_LOW_STRUCT         =       [ '>HHL',       namedtuple( "LOW", "max_stack max_locals code_length" ) ]

ARRAY_TYPE      =       { 
                           4 : "T_BOOLEAN",
                           5 : "T_CHAR",
                           6 : "T_FLOAT",
                           7 : "T_DOUBLE",
                           8 : "T_BYTE",
                           9 : "T_SHORT",
                           10 : "T_INT",
                           11 : "T_LONG",
                        }
INVERT_ARRAY_TYPE = dict([( ARRAY_TYPE[k][0], k ) for k in ARRAY_TYPE])


ACC_CLASS_FLAGS = {
                     0x0001 : [ "ACC_PUBLIC", "Declared public; may be accessed from outside its package." ],
                     0x0010 : [ "ACC_FINAL", "Declared final; no subclasses allowed." ],
                     0x0020 : [ "ACC_SUPER", "Treat superclass methods specially when invoked by the invokespecial instruction." ],
                     0x0200 : [ "ACC_INTERFACE", "Is an interface, not a class." ],
                     0x0400 : [ "ACC_ABSTRACT", "Declared abstract; may not be instantiated." ],
                  }
INVERT_ACC_CLASS_FLAGS = dict([( ACC_CLASS_FLAGS[k][0], k ) for k in ACC_CLASS_FLAGS])


ACC_FIELD_FLAGS = {
                     0x0001 : [ "ACC_PUBLIC", "Declared public; may be accessed from outside its package." ],
                     0x0002 : [ "ACC_PRIVATE", "Declared private; usable only within the defining class." ],
                     0x0004 : [ "ACC_PROTECTED", "Declared protected; may be accessed within subclasses." ],
                     0x0008 : [ "ACC_STATIC", "Declared static." ],
                     0x0010 : [ "ACC_FINAL", "Declared final; no further assignment after initialization." ],
                     0x0040 : [ "ACC_VOLATILE", "Declared volatile; cannot be cached." ],
                     0x0080 : [ "ACC_TRANSIENT", "Declared transient; not written or read by a persistent object manager." ],
                  }
INVERT_ACC_FIELD_FLAGS = dict([( ACC_FIELD_FLAGS[k][0], k ) for k in ACC_FIELD_FLAGS])


ACC_METHOD_FLAGS = {
                     0x0001 : [ "ACC_PUBLIC", "Declared public; may be accessed from outside its package." ],
                     0x0002 : [ "ACC_PRIVATE", "Declared private; accessible only within the defining class." ],
                     0x0004 : [ "ACC_PROTECTED", "Declared protected; may be accessed within subclasses." ],
                     0x0008 : [ "ACC_STATIC", "Declared static." ],
                     0x0010 : [ "ACC_FINAL", "Declared final; may not be overridden." ],
                     0x0020 : [ "ACC_SYNCHRONIZED", "Declared synchronized; invocation is wrapped in a monitor lock." ],
                     0x0100 : [ "ACC_NATIVE", "Declared native; implemented in a language other than Java." ],
                     0x0400 : [ "ACC_ABSTRACT", "Declared abstract; no implementation is provided." ],
                     0x0800 : [ "ACC_STRICT", "Declared strictfp; floating-point mode is FP-strict" ]
                  }
INVERT_ACC_METHOD_FLAGS = dict([( ACC_METHOD_FLAGS[k][0], k ) for k in ACC_METHOD_FLAGS])

class CpInfo(object) :
   """Generic class to manage constant info object"""
   def __init__(self, buff) :
      self.__tag = SV( '>B', buff.read_b(1) )

      self.__bytes = None
      self.__extra = 0

      tag_value = self.__tag.get_value()
      format = CONSTANT_INFO[ tag_value ][1]

      self.__name = CONSTANT_INFO[ tag_value ][0]

      self.format = SVs( format, CONSTANT_INFO[ tag_value ][2], buff.read( calcsize( format ) ) )

      # Utf8 value ?
      if tag_value == 1 :
         self.__extra = self.format.get_value().length
         self.__bytes = SVs( ">%ss" % self.format.get_value().length, namedtuple( CONSTANT_INFO[ tag_value ][0] + "_next", "bytes" ), buff.read( self.format.get_value().length ) )

   def get_format(self) :
      return self.format

   def get_name(self) :
      return self.__name

   def get_bytes(self) :
      return self.__bytes.get_value().bytes

   def set_bytes(self, name) :
      self.format.set_value( { "length" : len(name) } )
      self.__extra = self.format.get_value().length
      self.__bytes = SVs( ">%ss" % self.format.get_value().length, namedtuple( CONSTANT_INFO[ self.__tag.get_value() ][0] + "_next", "bytes" ), name )

   def get_length(self) :
      return self.__extra + calcsize( CONSTANT_INFO[ self.__tag.get_value() ][1] )
   
   def get_raw(self) :
      if self.__bytes != None :
         return self.format.get_value_buff() + self.__bytes.get_value_buff()
      return self.format.get_value_buff()

   def show(self) :
      if self.__bytes != None :
         print self.format.get_value(), self.__bytes.get_value()
      else :
         print self.format.get_value()

class MethodRef(CpInfo) :
   def __init__(self, class_manager, buff) :
      super(MethodRef, self).__init__( buff )

   def get_class_index(self) :
      return self.format.get_value().class_index

   def get_name_and_type_index(self) :
      return self.format.get_value().name_and_type_index

class InterfaceMethodRef(CpInfo) :
   def __init__(self, class_manager, buff) :
      super(InterfaceMethodRef, self).__init__( buff )

class FieldRef(CpInfo) :
   def __init__(self, class_manager, buff) :
      super(FieldRef, self).__init__( buff )

   def get_class_index(self) :
      return self.format.get_value().class_index

   def get_name_and_type_index(self) :
      return self.format.get_value().name_and_type_index

class Class(CpInfo) :
   def __init__(self, class_manager, buff) :
      super(Class, self).__init__( buff )

   def get_name_index(self) :
      return self.format.get_value().name_index

class Utf8(CpInfo) :
   def __init__(self, class_manager, buff) :
      super(Utf8, self).__init__( buff )

class String(CpInfo) :
   def __init__(self, class_manager, buff) :
      super(String, self).__init__( buff )

class Integer(CpInfo) :
   def __init__(self, class_manager, buff) :
      super(Integer, self).__init__( buff )

class Float(CpInfo) :
   def __init__(self, class_manager, buff) :
      super(Float, self).__init__( buff )

class Long(CpInfo) :
   def __init__(self, class_manager, buff) :
      super(Long, self).__init__( buff )

class Double(CpInfo) :
   def __init__(self, class_manager, buff) :
      super(Double, self).__init__( buff )

class NameAndType(CpInfo) :
   def __init__(self, class_manager, buff) :
      super(NameAndType, self).__init__( buff )

   def get_get_name_index(self) :
      return self.format.get_value().get_name_index

   def get_name_index(self) :
      return self.format.get_value().name_index

   def get_descriptor_index(self) :
      return self.format.get_value().descriptor_index

CONSTANT_INFO = {
         7 :    [ "CONSTANT_Class",             '>BH',  namedtuple( "CONSTANT_Class_info", "tag name_index" ), Class ],
         9 :    [ "CONSTANT_Fieldref",          '>BHH', namedtuple( "CONSTANT_Fieldref_info", "tag class_index name_and_type_index" ), FieldRef ],
         10 :   [ "CONSTANT_Methodref",         '>BHH', namedtuple( "CONSTANT_Methodref_info", "tag class_index name_and_type_index" ), MethodRef ],
         11 :   [ "CONSTANT_InterfaceMethodref", '>BHH', namedtuple( "CONSTANT_InterfaceMethodref_info", "tag class_index name_and_type_index" ), InterfaceMethodRef ],
         8 :    [ "CONSTANT_String",            '>BH',  namedtuple( "CONSTANT_String_info", "tag string_index" ), String ],
         3 :    [ "CONSTANT_Integer",           '>BL', namedtuple( "CONSTANT_Integer_info", "tag bytes" ), Integer ],
         4 :    [ "CONSTANT_Float",             '>BL', namedtuple( "CONSTANT_Float_info", "tag bytes" ), Float ],
         5 :    [ "CONSTANT_Long",              '>BLL', namedtuple( "CONSTANT_Long_info", "tag high_bytes low_bytes" ), Long ],
         6 :    [ "CONSTANT_Double",            '>BLL', namedtuple( "CONSTANT_Long_info", "tag high_bytes low_bytes" ), Double ],
         12 :   [ "CONSTANT_NameAndType",       '>BHH', namedtuple( "CONSTANT_NameAndType_info", "tag name_index descriptor_index" ), NameAndType ],
         1 :    [ "CONSTANT_Utf8",              '>BH', namedtuple( "CONSTANT_Utf8_info", "tag length" ), Utf8 ]
      }
INVERT_CONSTANT_INFO = dict([( CONSTANT_INFO[k][0], k ) for k in CONSTANT_INFO])                                                                                                                                                     
ITEM_Top = 0
ITEM_Integer = 1
ITEM_Float = 2
ITEM_Long = 4
ITEM_Double = 3
ITEM_Null = 5
ITEM_UninitializedThis = 6
ITEM_Object = 7
ITEM_Uninitialized = 8

VERIFICATION_TYPE_INFO = {
      ITEM_Top :                   [ "Top_variable_info", '>B', namedtuple( "Top_variable_info", "tag" ) ],
      ITEM_Integer :               [ "Integer_variable_info", '>B', namedtuple( "Integer_variable_info", "tag" ) ],
      ITEM_Float :                 [ "Float_variable_info", '>B', namedtuple( "Float_variable_info", "tag" ) ],
      ITEM_Long :                  [ "Long_variable_info", '>B', namedtuple( "Long_variable_info", "tag" ) ],
      ITEM_Double :                [ "Double_variable_info", '>B', namedtuple( "Double_variable_info", "tag" ) ],
      ITEM_Null :                  [ "Null_variable_info", '>B', namedtuple( "Null_variable_info", "tag" ) ],
      ITEM_UninitializedThis :     [ "UninitializedThis_variable_info", '>B', namedtuple( "UninitializedThis_variable_info", "tag" ) ],
      ITEM_Object :                [ "Object_variable_info", '>BH', namedtuple( "Object_variable_info", "tag cpool_index" ), [ ("cpool_index", "get_class") ] ],
      ITEM_Uninitialized :         [ "Uninitialized_variable_info", '>BH', namedtuple( "Uninitialized_variable_info", "tag offset" ) ],
   }

class FieldInfo : 
   """An object which represents a Field""" 
   def __init__(self, class_manager, buff) :
      self.__raw_buff = buff.read( calcsize( FIELD_INFO[0] ) ) 
      self.format = SVs( FIELD_INFO[0], FIELD_INFO[1], self.__raw_buff )

      self.__CM = class_manager
      self.__attributes = []

      for i in range(0, self.format.get_value().attributes_count) :
         ai = AttributeInfo( self.__CM, buff )
         self.__attributes.append( ai )

   def get_raw(self) :
      return self.__raw_buff + ''.join(x.get_raw() for x in self.__attributes)

   def get_length(self) :
      val = 0
      for i in self.__attributes :
         val += i.length
      return val + calcsize( FIELD_INFO[0] )

   def get_access(self) :
      return ACC_FIELD_FLAGS[ self.format.get_value().access_flags ][0]

   def set_access(self, value) :
      self.format.set_value( { "access_flags" : value } )

   def get_name(self) :
      return self.__CM.get_string( self.format.get_value().name_index )

   def set_name(self, name) :
      return self.__CM.set_string( self.format.get_value().name_index, name )

   def get_descriptor(self) :
      return self.__CM.get_string( self.format.get_value().descriptor_index )

   def set_descriptor(self, name) :
      return self.__CM.set_string( self.format.get_value().descriptor_index, name )

   def get_attributes(self) :
      return self.__attributes

   def show(self) :
      print self.format.get_value(), self.__CM.get_string( self.format.get_value().name_index )
      for i in self.__attributes :
         i.show()

class MethodInfo :
   """An object which represents a Method"""
   def __init__(self, class_manager, buff) :
      self.format = SVs( METHOD_INFO[0], METHOD_INFO[1], buff.read( calcsize( METHOD_INFO[0] ) ) )

      self.__CM = class_manager
      self.__code = None
      self.__attributes = []

      for i in range(0, self.format.get_value().attributes_count) :
         ai = AttributeInfo( self.__CM, buff ) 
         self.__attributes.append( ai )

         if ai.get_name() == "Code" :
            self.__code = ai

   def get_raw(self) :
      return self.format.get_value_buff() + ''.join(x.get_raw() for x in self.__attributes)
   
   def get_length(self) :
      val = 0
      for i in self.__attributes :
         val += i.length

      return val + calcsize( METHOD_INFO[0] )

   def get_attributes(self) :
      return self.__attributes

   def get_access(self) :
      return ACC_METHOD_FLAGS[ self.format.get_value().access_flags ][0]

   def set_access(self, value) :
      self.format.set_value( { "access_flags" : value } )

   def get_name(self) :
      return self.__CM.get_string( self.format.get_value().name_index )

   def set_name(self, name) :
      return self.__CM.set_string( self.format.get_value().name_index, name )

   def get_descriptor(self) :
      return self.__CM.get_string( self.format.get_value().descriptor_index )

   def set_descriptor(self, name) :
      return self.__CM.set_string( self.format.get_value().name_descriptor, name )

   def get_name_index(self) :
      return self.format.get_value().name_index

   def get_descriptor_index(self) :
      return self.format.get_value().descriptor_index

   def get_local_variables(self) :
      return self.get_code().get_local_variables()

   def get_code(self) :
      return self.__code.get_item()

   def set_name_index(self, name_index) :
      self.format.set_value( { "name_index" : name_index } )

   def set_descriptor_index(self, descriptor_index) :
      self.format.set_value( { "descriptor_index" : descriptor_index } )

   def set_cm(self, cm) :
      self.__CM = cm
      for i in self.__attributes :
         i.set_cm( cm )

   def with_descriptor(self, descriptor) :
      return descriptor == self.__CM.get_string( self.format.get_value().descriptor_index )

   def _patch_bytecodes(self) :
      return self.get_code()._patch_bytecodes()

   def show(self) :
      print "*" * 80
      print self.format.get_value(), self.__CM.get_string( self.format.get_value().name_index ), self.__CM.get_string( self.format.get_value().descriptor_index )
      for i in self.__attributes :
         i.show()
      print "*" * 80

class CreateString :
   """Create a specific String constant by given the name index"""
   def __init__(self, class_manager, bytes) :
      self.__string_index = class_manager.add_string( bytes )

   def get_raw(self) :
      tag_value = INVERT_CONSTANT_INFO[ "CONSTANT_String" ]
      buff = pack( CONSTANT_INFO[ tag_value ][1], tag_value, self.__string_index )

      return buff

class CreateInteger :
   """Create a specific Integer constant by given the name index"""
   def __init__(self, byte) :
      self.__byte = byte

   def get_raw(self) :
      tag_value = INVERT_CONSTANT_INFO[ "CONSTANT_Integer" ]
      buff = pack( CONSTANT_INFO[ tag_value ][1], tag_value, self.__byte )

      return buff

class CreateClass :
   """Create a specific Class constant by given the name index"""
   def __init__(self, class_manager, name_index) :
      self.__CM = class_manager

      self.__name_index = name_index

   def get_raw(self) :
      tag_value = INVERT_CONSTANT_INFO[ "CONSTANT_Class" ]
      buff = pack( CONSTANT_INFO[ tag_value ][1], tag_value, self.__name_index )

      return buff

class CreateNameAndType :
   """Create a specific NameAndType constant by given the name and the descriptor index"""
   def __init__(self, class_manager, name_index, descriptor_index) :
      self.__CM = class_manager

      self.__name_index = name_index
      self.__descriptor_index = descriptor_index

   def get_raw(self) :
      tag_value = INVERT_CONSTANT_INFO[ "CONSTANT_NameAndType" ]
      buff = pack( CONSTANT_INFO[ tag_value ][1], tag_value, self.__name_index, self.__descriptor_index )
      
      return buff

class CreateFieldRef :
   """Create a specific FieldRef constant by given the class and the NameAndType index"""
   def __init__(self, class_manager, class_index, name_and_type_index) :
      self.__CM = class_manager

      self.__class_index = class_index
      self.__name_and_type_index = name_and_type_index

   def get_raw(self) :
      tag_value = INVERT_CONSTANT_INFO[ "CONSTANT_Fieldref" ]
      buff = pack( CONSTANT_INFO[ tag_value ][1], tag_value, self.__class_index, self.__name_and_type_index )

      return buff

class CreateMethodRef :
   """Create a specific MethodRef constant by given the class and the NameAndType index"""
   def __init__(self, class_manager, class_index, name_and_type_index) :
      self.__CM = class_manager

      self.__class_index = class_index
      self.__name_and_type_index = name_and_type_index

   def get_raw(self) :
      tag_value = INVERT_CONSTANT_INFO[ "CONSTANT_Methodref" ]
      buff = pack( CONSTANT_INFO[ tag_value ][1], tag_value, self.__class_index, self.__name_and_type_index )

      return buff

class CreateCodeAttributeInfo :
   """Create a specific CodeAttributeInfo by given bytecodes (into an human readable format)"""
   def __init__(self, class_manager, codes) :
      self.__CM = class_manager

#ATTRIBUTE_INFO  =               [ '>HL', namedtuple("AttributeInfo", "attribute_name_index attribute_length") ]
      self.__attribute_name_index = self.__CM.get_string_index( "Code" )
      self.__attribute_length = 0
########

# CODE_LOW_STRUCT         =       [ '>HHL', namedtuple( "LOW", "max_stack max_locals code_length" ) ]      
      self.__max_stack = 1 
      self.__max_locals = 2 
      self.__code_length = 0
########

# CODE
      raw_buff = ""

      for i in codes :
         op_name = i[0]         
         op_value = INVERT_JAVA_OPCODES[ op_name ]                  
         raw_buff += pack( '>B', op_value )
      
         if len( JAVA_OPCODES[ op_value ] ) > 1 :
            r_function, v_function, r_buff, r_format, f_function = EXTRACT_INFORMATION( op_value )
            raw_buff += pack(r_format, *v_function( *i[1:] ) )

      self.__code = JavaCode( self.__CM, raw_buff )
      self.__code_length = len( raw_buff )
######## 

# EXCEPTION 
      # u2 exception_table_length;                                                                                                                                                                                            
      self.__exception_table_length = 0
      
         # {            u2 start_pc;
         #              u2 end_pc;                                                          
         #              u2  handler_pc;                                
         #              u2  catch_type;                                     
         # }      exception_table[exception_table_length];
      self.__exception_table = []
########

# ATTRIBUTES         
      # u2 attributes_count;         
      self.__attributes_count = 0
                                             
      # attribute_info attributes[attributes_count];         
      self.__attributes = []
########

      # FIXME : remove calcsize
      self.__attribute_length = calcsize( ATTRIBUTE_INFO[0] ) + \
                                calcsize( CODE_LOW_STRUCT[0] ) + \
                                self.__code_length + \
                                calcsize('>H') + \
                                calcsize('>H')

   def get_raw(self) :
      return pack( ATTRIBUTE_INFO[0], self.__attribute_name_index, self.__attribute_length ) + \
             pack( CODE_LOW_STRUCT[0], self.__max_stack, self.__max_locals, self.__code_length ) + \
             self.__code.get_raw() + \
             pack( '>H', self.__exception_table_length ) + \
             ''.join( i.get_raw() for i in self.__exception_table ) + \
             pack( '>H', self.__attributes_count ) + \
             ''.join( i.get_raw() for i in self.__attributes )


# METHOD_INFO     =               [ '>HHHH', namedtuple("MethodInfo", "access_flags name_index descriptor_index attributes_count") ]                                                                                              
class CreateMethodInfo :
   """Create a specific MethodInfo by given the name, the prototype and the code (into an human readable format) of the "new" method"""
   def __init__(self, class_manager, name, proto, codes) :
      self.__CM = class_manager

      access_flags_value = proto[0]
      return_value = proto[1]
      arguments_value = proto[2]
      
      self.__access_flags = INVERT_ACC_METHOD_FLAGS[ access_flags_value ]
      
      self.__name_index = self.__CM.get_string_index( name )
      if self.__name_index == -1 :
         self.__name_index = self.__CM.add_string( name )   

      proto_final = "(" + arguments_value + ")" + return_value
      self.__descriptor_index = self.__CM.get_string_index( proto_final )
      if self.__descriptor_index == -1 :
         self.__descriptor_index = self.__CM.add_string( proto_final )

      self.__attributes = []

      self.__attributes.append( CreateCodeAttributeInfo( self.__CM, codes ) )

   def get_raw(self) :
      buff = pack( METHOD_INFO[0], self.__access_flags, self.__name_index, self.__descriptor_index, len(self.__attributes) )

      for i in self.__attributes :
         buff += i.get_raw()

      return buff

class JBC :
   """JBC manages each bytecode with the value, name, raw buffer and special functions"""
   # special --> ( r_function, v_function, r_buff, r_format, f_function )
   def __init__(self, class_manager, op_name, raw_buff, special=None) :
      self.__CM = class_manager
      self.__op_name = op_name
      self.__raw_buff = raw_buff
 
      self.__special = special 
      self.__special_value = None

      self._load()

   def _load(self) :
      if self.__special != None :
         ntuple = namedtuple( self.__op_name, self.__special[2] )
         x = ntuple._make( unpack( self.__special[3], self.__raw_buff[1:] ) )

         if self.__special[4] == None :
            self.__special_value = self.__special[0]( x )
         else :
            self.__special_value = getattr(self.__CM, self.__special[4])( self.__special[0]( x ) )

   def reload(self, raw_buff) :
      """Reload the bytecode with a new raw buffer"""
      self.__raw_buff = raw_buff
      self._load()

   def set_cm(self, cm) :
      self.__CM = cm

   def get_length(self) :
      """Return the length of the bytecode"""
      return len( self.__raw_buff )

   def get_raw(self) :
      """Return the current raw buffer of the bytecode"""
      return self.__raw_buff

   def get_name(self) :
      """Return the name of the bytecode"""
      return self.__op_name

   def get_operands(self) :
      """Return the operands of the bytecode"""
      if isinstance( self.__special_value, list ):
         if len(self.__special_value) == 1 :
            return self.__special_value[0]
      return self.__special_value

   def adjust_r(self, pos, pos_modif, len_modif) :
      """Adjust the bytecode (if necessary (in this cas the bytecode is a branch bytecode)) when a bytecode has been removed"""
#      print self.__op_name, pos, pos_modif, len_modif, self.__special_value, type(pos), type(pos_modif), type(len_modif), type(self.__special_value)

      if pos > pos_modif : 
         if (self.__special_value + pos) < (pos_modif) :
#            print "MODIF +", self.__special_value, len_modif,
            self.__special_value += len_modif
#            print self.__special_value
            self.__raw_buff = pack( '>B', INVERT_JAVA_OPCODES[ self.__op_name ] ) + pack(self.__special[3], *self.__special[1]( self.__special_value ) )

      elif pos < pos_modif :
         if (self.__special_value + pos) > (pos_modif) :
#            print "MODIF -", self.__special_value, len_modif,
            self.__special_value -= len_modif            
#            print self.__special_value
            self.__raw_buff = pack( '>B', INVERT_JAVA_OPCODES[ self.__op_name ] ) + pack(self.__special[3], *self.__special[1]( self.__special_value ) )

   def adjust_i(self, pos, pos_modif, len_modif) :
      """Adjust the bytecode (if necessary (in this cas the bytecode is a branch bytecode)) when a bytecode has been inserted"""
      #print self.__op_name, pos, pos_modif, len_modif, self.__special_value, type(pos), type(pos_modif), type(len_modif), type(self.__special_value)

      if pos > pos_modif :
         if (self.__special_value + pos) < (pos_modif) :
#            print "MODIF +", self.__special_value, len_modif,
            self.__special_value -= len_modif
#            print self.__special_value            
            self.__raw_buff = pack( '>B', INVERT_JAVA_OPCODES[ self.__op_name ] ) + pack(self.__special[3], *self.__special[1]( self.__special_value ) )

      elif pos < pos_modif :
         if (self.__special_value + pos) > (pos_modif) :
#            print "MODIF -", self.__special_value, len_modif,
            self.__special_value += len_modif
#            print self.__special_value            
            self.__raw_buff = pack( '>B', INVERT_JAVA_OPCODES[ self.__op_name ] ) + pack(self.__special[3], *self.__special[1]( self.__special_value ) )

   def show(self, pos) :
      """Show the bytecode at a specific position
      
         pos - the position into the bytecodes (integer)
      """
      if self.__special_value == None :
         print self.__op_name
      else :
         if self.__op_name in BRANCH_JAVA_OPCODES :
            print self.__op_name, self.__special_value, self.__special_value + pos
         else : 
            print self.__op_name, self.__special_value

class JavaCode :
   """JavaCode manages a list of bytecode to a specific method, by decoding a raw buffer and transform each bytecode into a JBC object"""
   def __init__(self, class_manager, buff) :
      self.__CM = class_manager
      
      self.__raw_buff = buff
      self.__bytecodes = []
      self.__maps = []
      self.__branches = []

      i = 0
      while i < len(self.__raw_buff) :
         op_value = unpack( '>B', self.__raw_buff[i])[0]
         if op_value in JAVA_OPCODES :
            if len( JAVA_OPCODES[ op_value ] ) > 2 : 
               r_function, v_function, r_buff, r_format, f_function = EXTRACT_INFORMATION( op_value )
               len_format = calcsize(r_format)

               raw_buff = self.__raw_buff[ i : i + 1 + len_format ]
               
               jbc = JBC( class_manager, JAVA_OPCODES[ op_value ][0], raw_buff, ( r_function, v_function, r_buff, r_format, f_function ) )
               self.__bytecodes.append( jbc )

               i += len_format 
            else : 
               self.__bytecodes.append( JBC( class_manager, JAVA_OPCODES[ op_value ][0], self.__raw_buff[ i ] ) )
         else :
            bytecode.Exit( "op_value 0x%x is unknown" % op_value ) 

         i += 1

      # Create branch bytecodes list
      idx = 0
      nb = 0
      for i in self.__bytecodes :
         self.__maps.append( idx )
         
         if i.get_name() in BRANCH_JAVA_OPCODES :
            self.__branches.append( nb )

         idx += i.get_length()
         nb += 1

   def _patch_bytecodes(self) :
      methods = []
      for i in self.__bytecodes :
         if "invoke" in i.get_name() :
            operands = i.get_operands()
            methods.append( operands )
            op_value = INVERT_JAVA_OPCODES[ i.get_name() ]      
            raw_buff = pack( '>B', op_value )

            r_function, v_function, r_buff, r_format, f_function = EXTRACT_INFORMATION( op_value )

            new_class_index = self.__CM.create_class( operands[0] )
            new_name_and_type_index = self.__CM.create_name_and_type( operands[1], operands[2] )

            self.__CM.create_method_ref( new_class_index, new_name_and_type_index )

            value = getattr( self.__CM, JAVA_OPCODES[ op_value ][5] )( *operands[0:] )    
            if value == -1 :            
               bytecode.Exit( "Unable to found method " + str(operands) )

            raw_buff += pack(r_format, *v_function( value ) )

            i.reload( raw_buff )
         elif "anewarray" in i.get_name() :
            operands = i.get_operands()
            op_value = INVERT_JAVA_OPCODES[ i.get_name() ]            
            raw_buff = pack( '>B', op_value )

            r_function, v_function, r_buff, r_format, f_function = EXTRACT_INFORMATION( op_value )

            new_class_index = self.__CM.create_class( operands[0] )
            
            raw_buff += pack(r_format, *v_function( new_class_index ) )

            i.reload( raw_buff )

         elif "getstatic" == i.get_name() :
            operands = i.get_operands()
            op_value = INVERT_JAVA_OPCODES[ i.get_name() ]      
            raw_buff = pack( '>B', op_value )

            r_function, v_function, r_buff, r_format, f_function = EXTRACT_INFORMATION( op_value )

            new_class_index = self.__CM.create_class( operands[0] )
            new_name_and_type_index = self.__CM.create_name_and_type( operands[1], operands[2] )

            self.__CM.create_field_ref( new_class_index, new_name_and_type_index )


            value = getattr( self.__CM, JAVA_OPCODES[ op_value ][5] )( *operands[1:] )    
            if value == -1 :            
               bytecode.Exit( "Unable to found method " + str(operands) )

            raw_buff += pack(r_format, *v_function( value ) )

            i.reload( raw_buff )

         elif "ldc" == i.get_name() :
            operands = i.get_operands()
            op_value = INVERT_JAVA_OPCODES[ i.get_name() ]            
            raw_buff = pack( '>B', op_value )

            r_function, v_function, r_buff, r_format, f_function = EXTRACT_INFORMATION( op_value )

            if operands[0] != "CONSTANT_Integer" and operands[0] != "CONSTANT_String" :
               bytecode.Exit( "...." )

            if operands[0] == "CONSTANT_Integer" :
               new_int_index = self.__CM.create_integer( operands[1] )
               raw_buff += pack(r_format, *v_function( new_int_index ) )
            
            elif operands[0] == "CONSTANT_String" :
               new_string_index = self.__CM.create_string( operands[1] )
               
               raw_buff += pack(r_format, *v_function( new_string_index ) )
        
            i.reload( raw_buff )
            
         elif "new" == i.get_name() :
            operands = i.get_operands()
            op_value = INVERT_JAVA_OPCODES[ i.get_name() ]            
            raw_buff = pack( '>B', op_value )

            r_function, v_function, r_buff, r_format, f_function = EXTRACT_INFORMATION( op_value )

            new_class_index = self.__CM.create_class( operands[0] )
            
            raw_buff += pack(r_format, *v_function( new_class_index ) )

            i.reload( raw_buff )

      return methods

   def get(self) :
      return self.__bytecodes

   def get_raw(self) :
      return ''.join(x.get_raw() for x in self.__bytecodes)

   def show(self) :
      nb = 0
      print repr( self.__raw_buff )
      for i in self.__bytecodes :
         print nb, self.__maps[nb], "\t", 
         i.show( self.__maps[nb] )
         nb += 1

   def get_at(self, idx) :
      return self.__bytecodes[ idx ]

   def remove_at(self, idx) :
      """Remove bytecode at a specific index"""
      val = self.__bytecodes[idx]
      val_m = self.__maps[idx]

      # Remove the index if it's in our branch list
      if idx in self.__branches :
         self.__branches.remove( idx )
      
      # Adjust each branch
      for i in self.__branches :
         self.__bytecodes[i].adjust_r( self.__maps[i], val_m, val.get_length() )
  
      # Remove it ! 
      self.__maps.pop(idx)
      self.__bytecodes.pop(idx)

      # Adjust branch and map list
      self._adjust_maps( val_m, val.get_length() * -1 )
      self._adjust_branches( idx, -1 )

      return val.get_length()
   
   def _adjust_maps(self, val, size) :
      nb = 0 
      for i in self.__maps :
         if i > val :
            self.__maps[ nb ] = i + size
         nb = nb + 1

   def _adjust_maps_i(self, val, size) :
      nb = 0 
      x = 0
      for i in self.__maps :
         if i == val :
            x+=1
         
         if x == 2 :
            self.__maps[ nb ] = i + size

         if i > val :
            self.__maps[ nb ] = i + size
         nb = nb + 1

   def _adjust_branches(self, val, size) :
      nb = 0
      for i in self.__branches :
         if i > val :
            self.__branches[ nb ] = i + size 
         nb += 1

   def insert_at(self, idx, bytecode) :
      """Insert bytecode at a specific index"""

      # Get the op_value and add it to the raw_buff
      op_name = bytecode[0]
      op_value = INVERT_JAVA_OPCODES[ op_name ]
      raw_buff = pack( '>B', op_value )

      new_jbc = None

      # If it's an op_value with args, we must handle that !
      if len( JAVA_OPCODES[ op_value ] ) > 1 :

         # Find information about the op_value
         r_function, v_function, r_buff, r_format, f_function = EXTRACT_INFORMATION( op_value )     
        
         # Special values for this op_value (advanced bytecode)
         if len( JAVA_OPCODES[ op_value ] ) == 6 :
            
            
            value = getattr( self.__CM, JAVA_OPCODES[ op_value ][5] )( *bytecode[1:] )
            if value == -1 :
               bytecode.Exit( "Unable to found method ", str(bytecode[1:]) )

            raw_buff += pack(r_format, *v_function( value ) )
         else :
            raw_buff += pack(r_format, *v_function( *bytecode[1:] ) )
 
         new_jbc = JBC(self.__CM, op_name, raw_buff, ( r_function, v_function, r_buff, r_format, f_function ) )
      else :
         new_jbc = JBC(self.__CM, op_name, raw_buff)

      # Adjust each branch with the new insertion
      val_m = self.__maps[ idx ]
      for i in self.__branches :
         self.__bytecodes[i].adjust_i( self.__maps[i], val_m, new_jbc.get_length() )
     
      # Insert the new bytecode at the correct index
      # Adjust maps + branches
      self.__bytecodes.insert( idx, new_jbc ) 
      self.__maps.insert( idx, val_m )
      self._adjust_maps_i( val_m, new_jbc.get_length() )
      
      self._adjust_branches( idx, 1 )
     
      # Add it to the branches if it's a correct op_value 
      if new_jbc.get_name() in BRANCH_JAVA_OPCODES :
         self.__branches.append( idx )

      # return the length of the raw_buff
      return len(raw_buff)

   def remplace_at(self, idx, bytecode) :
      """Remplace bytecode at a specific index by another bytecode (remplace = remove + insert)"""
      size = self.remove_at(idx) * (-1)
      size += self.insert_at(idx, bytecode)

      return size

   def set_cm(self, cm) :
      self.__CM = cm
      for i in self.__bytecodes :
         i.set_cm( cm )

class BasicAttribute(object) :
   def __init__(self) :
      self.__attributes = []

   def get_attributes(self) :
      return self.__attributes

   def set_cm(self, cm) :
      self.__CM = cm

class CodeAttribute(BasicAttribute) :
   def __init__(self, class_manager, buff) :
      self.__CM = class_manager
      
      super(CodeAttribute, self).__init__()
      # u2 attribute_name_index;
      # u4 attribute_length;         
      
      # u2 max_stack;                  
      # u2 max_locals;                      
      # u4 code_length;   
      # u1 code[code_length];                        
      self.low_struct = SVs( CODE_LOW_STRUCT[0], CODE_LOW_STRUCT[1], buff.read( calcsize(CODE_LOW_STRUCT[0]) ) ) 

      self.__code = JavaCode( class_manager, buff.read( self.low_struct.get_value().code_length ) )
      
      # u2 exception_table_length;
      self.exception_table_length = SV( '>H', buff.read(2) )
  
      # {            u2 start_pc;
      #              u2 end_pc;                                  
      #              u2  handler_pc;                                
      #              u2  catch_type;                                     
      # }      exception_table[exception_table_length];
      self.__exception_table = []
      for i in range(0, self.exception_table_length.get_value()) :
         et = SVs( EXCEPTION_TABLE[0], EXCEPTION_TABLE[1], buff.read( calcsize(EXCEPTION_TABLE[0]) ) )
         self.__exception_table.append( et )

      # u2 attributes_count;
      self.attributes_count = SV( '>H', buff.read(2) ) 
      
      # attribute_info attributes[attributes_count];
      self.__attributes = []
      for i in range(0, self.attributes_count.get_value()) :
         ai = AttributeInfo( self.__CM, buff ) 
         self.__attributes.append( ai )

   def get_attributes(self) :
      return self.__attributes

   def get_exceptions(self) :
      return self.__exception_table

   def get_raw(self) :
      return self.low_struct.get_value_buff() +                          \
             self.__code.get_raw() +                                       \
             self.exception_table_length.get_value_buff() +              \
             ''.join(x.get_value_buff() for x in self.__exception_table) + \
             self.attributes_count.get_value_buff()                    + \
             ''.join(x.get_raw() for x in self.__attributes)

   def get_max_stack(self) :
      return self.low_struct.get_value().max_stack

   def get_max_locals(self) :
      return self.low_struct.get_value().max_locals

   def get_local_variables(self) :
      for i in self.__attributes :
         if i.get_name() == "StackMapTable" :
            return i.get_item().get_local_variables()
      return []

   def get_bc(self) :
      return self.__code

   # FIXME : show* --> add exceptions
   def show_info(self) :
      print "!" * 70
      print self.low_struct.get_value()
      bytecode._Print( "ATTRIBUTES_COUNT", self.attributes_count.get_value() )
      for i in self.__attributes :
         i.show()
      print "!" * 70

   def show(self) :
      print "!" * 70
      print self.low_struct.get_value()
      self.__code.show()
      bytecode._Print( "ATTRIBUTES_COUNT", self.attributes_count.get_value() )
      for i in self.__attributes :
         i.show()
      print "!" * 70

   def _patch_bytecodes(self) :
      return self.__code._patch_bytecodes()

   def remplace_at(self, idx, bytecode) :
      size = self.__code.remplace_at(idx, bytecode)
      
      # Adjust the length of our bytecode
      self.low_struct.set_value( { "code_length" : self.low_struct.get_value().code_length + size } )

   def remove_at(self, idx) :
      size = self.__code.remove_at(idx)
      # Adjust the length of our bytecode
      self.low_struct.set_value( { "code_length" : self.low_struct.get_value().code_length - size } )

   def removes_at(self, l_idx) :
      i = 0
      while i < len(l_idx) :
         self.remove_at( l_idx[i] )

         j = i + 1
         while j < len(l_idx) :
            if l_idx[j] > l_idx[i] :
               l_idx[j] -= 1

            j += 1

         i += 1

   def insert_at(self, idx, bytecode) :
      size = self.__code.insert_at(idx, bytecode)
      # Adjust the length of our bytecode
      self.low_struct.set_value( { "code_length" : self.low_struct.get_value().code_length + size } )

   def get_at(self, idx) :
      return self.__code.get_at(idx)

   def gets_at(self, l_idx) :
      return [ self.__code.get_at(i) for i in l_idx ]

   def set_cm(self, cm) :
      self.__CM = cm
      for i in self.__attributes :
         i.set_cm( cm )
      self.__code.set_cm( cm )

   def _fix_attributes(self, new_cm) :
      for i in self.__attributes :
         i._fix_attributes( new_cm )

class SourceFileAttribute(BasicAttribute) :
   def __init__(self, buff) :
      super(SourceFileAttribute, self).__init__()
      # u2 attribute_name_index;
      # u4 attribute_length;
      
      # u2 sourcefile_index;
      self.sourcefile_index = SV( '>H', buff.read(2) )
      
   def get_raw(self) :
      return self.sourcefile_index.get_value_buff()

   def show(self) :
      print self.sourcefile_index

class LineNumberTableAttribute(BasicAttribute) :
   def __init__(self, buff) :
      super(LineNumberTableAttribute, self).__init__()
      # u2 attribute_name_index;        
      # u4 attribute_length;

      # u2 line_number_table_length;
      # {  u2 start_pc;        
      #    u2 line_number;            
      # } line_number_table[line_number_table_length];

      self.line_number_table_length = SV( '>H', buff.read( 2 ) )

      self.__line_number_table = []
      for i in range(0, self.line_number_table_length.get_value()) :
         lnt = SVs( LINE_NUMBER_TABLE[0], LINE_NUMBER_TABLE[1], buff.read( 4 ) )
         self.__line_number_table.append( lnt )

   def get_raw(self) :
      return self.line_number_table_length.get_value_buff() + \
             ''.join(x.get_value_buff() for x in self.__line_number_table)

   def get_line_number_table(self) :
      return self.__line_number_table

   def show(self) :
      bytecode._Print("LINE_NUMBER_TABLE_LENGTH", self.line_number_table_length.get_value())
      for x in self.__line_number_table :
         print "\t", x.get_value()

   def _fix_attributes(self, new_cm) :
      pass

class LocalVariableTableAttribute(BasicAttribute) :
   def __init__(self, buff) :
      super(LocalVariableTableAttribute, self).__init__()
      # u2 attribute_name_index;
      # u4 attribute_length;
        
      # u2 local_variable_table_length;
      # {  u2 start_pc;
      #    u2 length;           
      #    u2 name_index;   
      #    u2 descriptor_index;                         
      #    u2 index;        
      # } local_variable_table[local_variable_table_length];
      self.local_variable_table_length = SV( '>H', buff.read(2) )

      self.__local_variable_table = []
      for i in range(0, self.local_variable_table_length.get_value()) :
         lvt = SVs( LOCAL_VARIABLE_TABLE[0], LOCAL_VARIABLE_TABLE[1], buff.read( 10 ) )

         self.__local_variable_table.append( lvt )

   def get_raw(self) :
      return self.local_variable_table_length.get_value_buff() + \
             ''.join(x.get_value_buff() for x in self.__local_variable_table)

   def show(self) :
      print self.local_variable_table_length 
      for x in self.__local_variable_table :
         print x.get_value()

class ExceptionsAttribute(BasicAttribute) :
   def __init__(self, buff) :
      super(ExceptionsAttribute, self).__init__()
      # u2 attribute_name_index;      
      # u4 attribute_length;

      # u2 number_of_exceptions;
      # u2 exception_index_table[number_of_exceptions];
      self.number_of_exceptions = SV( '>H', buff.read(2) )

      self.__exception_index_table = []
      for i in range(0, self.number_of_exceptions.get_value()) :
         self.__exception_index_table.append( SV( '>H', buff.read(2) ) )

   def get_raw(self) :
      return self.number_of_exceptions.get_value_buff() + ''.join(x.get_value_buff() for x in self.__exception_index_table)

   def get_exception_index_table(self) :
      return self.__exception_index_table

   def show(self) :
      print self.number_of_exceptions
      for i in self.__exception_index_table :
         print "\t", i

class VerificationTypeInfo :
   def __init__(self, class_manager, buff) :
      self.__CM = class_manager
      tag = SV( '>B', buff.read_b(1) ).get_value()

      if tag not in VERIFICATION_TYPE_INFO :
         bytecode.Exit( "tag not in VERIFICATION_TYPE_INFO" )

      format = VERIFICATION_TYPE_INFO[ tag ][1]
      self.format = SVs( format, VERIFICATION_TYPE_INFO[ tag ][2], buff.read( calcsize( format ) ) )

   def get_raw(self) :
      return self.format.get_value_buff()

   def show(self) :
      general_format = self.format.get_value()
      if len( VERIFICATION_TYPE_INFO[ general_format.tag ] ) > 3 :
         print general_format,
         for (i,j) in VERIFICATION_TYPE_INFO[ general_format.tag ][3] :
            print getattr(self.__CM, j)( getattr(general_format, i) )
      else :
         print general_format

   def _fix_attributes(self, new_cm) :
      general_format = self.format.get_value()

      if len( VERIFICATION_TYPE_INFO[ general_format.tag ] ) > 3 :
         for (i,j) in VERIFICATION_TYPE_INFO[ general_format.tag ][3] :
            # Fix the first object which is the current class
            if getattr(self.__CM, j)( getattr(general_format, i) )[0] == self.__CM.get_this_class_name() :
               self.format.set_value( { "cpool_index" : new_cm.get_this_class() } )
            # Fix other objects
            else :
               new_class_index = new_cm.create_class( getattr(self.__CM, j)( getattr(general_format, i) )[0] )
               self.format.set_value( { "cpool_index" : new_class_index } )

   def set_cm(self, cm) :
      self.__CM = cm

class FullFrame :
   def __init__(self, class_manager, buff) :
      self.__CM = class_manager
      # u1 frame_type = FULL_FRAME; /* 255 */
      # u2 offset_delta;
      # u2 number_of_locals;
      self.frame_type = SV( '>B', buff.read(1) )
      self.offset_delta = SV( '>H', buff.read(2) )
      self.number_of_locals = SV( '>H', buff.read(2) )

      # verification_type_info locals[number_of_locals];
      self.__locals = []
      for i in range(0, self.number_of_locals.get_value()) :
         self.__locals.append( VerificationTypeInfo( self.__CM, buff ) )

      # u2 number_of_stack_items;
      self.number_of_stack_items = SV( '>H', buff.read(2) )
      # verification_type_info stack[number_of_stack_items];
      self.__stack = []
      for i in range(0, self.number_of_stack_items.get_value()) :
         self.__stack.append( VerificationTypeInfo( self.__CM, buff ) )
    
   def get_locals(self) :
      return self.__locals

   def get_raw(self) :
     return self.frame_type.get_value_buff() + \
            self.offset_delta.get_value_buff() + \
            self.number_of_locals.get_value_buff() + \
            ''.join(x.get_raw() for x in self.__locals) + \
            self.number_of_stack_items.get_value_buff() + \
            ''.join(x.get_raw() for x in self.__stack) 

   def show(self) :
      print "#" * 60
      bytecode._Print("\tFULL_FRAME", self.frame_type.get_value())
      bytecode._Print("\tOFFSET_DELTA", self.offset_delta.get_value())
      
      bytecode._Print("\tNUMBER_OF_LOCALS", self.number_of_locals.get_value())
      for i in self.__locals :
         i.show()

      bytecode._Print("\tNUMBER_OF_STACK_ITEMS", self.number_of_stack_items.get_value())
      for i in self.__stack :
         i.show()

      print "#" * 60

   def _fix_attributes(self, new_cm) :
      for i in self.__locals :
         i._fix_attributes( new_cm )

   def set_cm(self, cm) :
      self.__CM = cm
      for i in self.__locals :
         i.set_cm( cm )

class ChopFrame :
   def __init__(self, buff) :
      # u1 frame_type=CHOP; /* 248-250 */
      # u2 offset_delta;
      self.frame_type = SV( '>B', buff.read(1) )
      self.offset_delta = SV( '>H', buff.read(2) )

   def get_raw(self) :
      return self.frame_type.get_value_buff() + self.offset_delta.get_value_buff()

   def show(self) :
      print "#" * 60
      bytecode._Print("\tCHOP_FRAME", self.frame_type.get_value())
      bytecode._Print("\tOFFSET_DELTA", self.offset_delta.get_value())
      print "#" * 60

   def _fix_attributes(self, cm) :
      pass

   def set_cm(self, cm) :
      pass

class SameFrame :
   def __init__(self, buff) :
      # u1 frame_type = SAME;/* 0-63 */
      self.frame_type = SV( '>B', buff.read(1) )

   def get_raw(self) :
      return self.frame_type.get_value_buff()

   def show(self) :
      print "#" * 60
      bytecode._Print("\tSAME_FRAME", self.frame_type.get_value())
      print "#" * 60

   def _fix_attributes(self, new_cm) :
      pass

   def set_cm(self, cm) :
      pass
      
   def show(self) :
      print "#" * 60
      bytecode._Print("\tSAME_LOCALS_1_STACK_ITEM_FRAME_EXTENDED", self.frame_type.get_value())
      print "#" * 60

class SameLocals1StackItemFrame :
   def __init__(self, class_manager, buff) :
      self.__CM = class_manager
      # u1 frame_type = SAME_LOCALS_1_STACK_ITEM;/* 64-127 */
      # verification_type_info stack[1];
      self.frame_type = SV( '>B', buff.read(1) )
      self.stack = VerificationTypeInfo( self.__CM, buff )

   def show(self) :
      print "#" * 60
      bytecode._Print("\tSAME_LOCALS_1_STACK_ITEM_FRAME", self.frame_type.get_value())
      self.stack.show()
      print "#" * 60

   def get_raw(self) :
      return self.frame_type.get_value_buff() + self.stack.get_value_buff()

   def _fix_attributes(self, new_cm) :
      pass

   def set_cm(self, cm) :
      self.__CM = cm
      
class SameLocals1StackItemFrameExtended :
   def __init__(self, class_manager, buff) :
      self.__CM = class_manager
      # u1 frame_type = SAME_LOCALS_1_STACK_ITEM_EXTENDED; /* 247 */
      # u2 offset_delta;        
      # verification_type_info stack[1];
      self.frame_type = SV( '>B', buff.read(1) )
      self.offset_delta = SV( '>H', buff.read(2) )
      self.stack = VerificationTypeInfo( self.__CM, buff )

   def get_raw(self) :
      return self.frame_type.get_value_buff() + self.offset_delta.get_value_buff() + self.stack.get_value_buff()

   def _fix_attributes(self, new_cm) :
      pass

   def set_cm(self, cm) :
      self.__CM = cm
      
   def show(self) :
      print "#" * 60
      bytecode._Print("\tSAME_LOCALS_1_STACK_ITEM_FRAME_EXTENDED", self.frame_type.get_value())
      bytecode._Print("\tOFFSET_DELTA", self.offset_delta.get_value())
      self.stack.show()
      print "#" * 60

class SameFrameExtended :
   def __init__(self, buff) :
      # u1 frame_type = SAME_FRAME_EXTENDED;/* 251*/
      # u2 offset_delta;
      self.frame_type = SV( '>B', buff.read(1) )      
      self.offset_delta = SV( '>H', buff.read(2) )

   def get_raw(self) :
      return self.frame_type.get_value_buff() + self.offset_delta.get_value_buff()

   def _fix_attributes(self, cm) :
      pass

   def set_cm(self, cm) :
      pass

   def show(self) :
      print "#" * 60
      bytecode._Print("\tSAME_FRAME_EXTENDED", self.frame_type.get_value())
      bytecode._Print("\tOFFSET_DELTA", self.offset_delta.get_value())
      print "#" * 60

class AppendFrame :
   def __init__(self, class_manager, buff) :
      self.__CM = class_manager
      # u1 frame_type = APPEND; /* 252-254 */
      # u2 offset_delta;
      self.frame_type = SV( '>B', buff.read(1) )      
      self.offset_delta = SV( '>H', buff.read(2) )
      
      # verification_type_info locals[frame_type -251];
      self.__locals = []
      k = self.frame_type.get_value() - 251
      for i in range(0, k) :
         self.__locals.append( VerificationTypeInfo( self.__CM, buff ) )

   def get_locals(self) :
      return self.__locals

   def show(self) :
      print "#" * 60
      bytecode._Print("\tAPPEND_FRAME", self.frame_type.get_value())
      bytecode._Print("\tOFFSET_DELTA", self.offset_delta.get_value())

      for i in self.__locals :
         i.show()

      print "#" * 60

   def get_raw(self) :
      return self.frame_type.get_value_buff() + \
             self.offset_delta.get_value_buff() + \
             ''.join(x.get_raw() for x in self.__locals)

   def _fix_attributes(self, new_cm) :
      for i in self.__locals :
         i._fix_attributes( new_cm )

   def set_cm(self, cm) :
      self.__CM = cm
      for i in self.__locals :
         i.set_cm( cm )

class StackMapTableAttribute(BasicAttribute) :
   def __init__(self, class_manager, buff) :
      self.__CM = class_manager
      
      super(StackMapTableAttribute, self).__init__()
      # u2 attribute_name_index;
      # u4 attribute_length
      
      # u2 number_of_entries;
      self.number_of_entries = SV( '>H', buff.read(2) )

      # stack_map_frame entries[number_of_entries];
      self.__entries = []
      for i in range(0, self.number_of_entries.get_value()) :
         frame_type = SV( '>B', buff.read_b(1) ).get_value()

         if frame_type >= 0 and frame_type <= 63 :
            self.__entries.append( SameFrame( buff ) )
         elif frame_type >= 64 and frame_type <= 127 :
            self.__entries.append( SameLocals1StackItemFrame( self.__CM, buff ) )
         elif frame_type == 247 :
            self.__entries.append( SameLocals1StackItemFrameExtended( self.__CM, buff ) )
         elif frame_type >= 248 and frame_type <= 250 :
            self.__entries.append( ChopFrame( buff ) )
         elif frame_type == 251 :
            self.__entries.append( SameFrameExtended( buff ) )
         elif frame_type >= 252 and frame_type <= 254 :
            self.__entries.append( AppendFrame( self.__CM, buff ) )
         elif frame_type == 255 : 
            self.__entries.append( FullFrame( self.__CM, buff ) )
         else : 
            bytecode.Exit( "Frame type %d is unknown" % frame_type )

   def get_entries(self) :
      return self.__entries

   def get_local_variables(self) :
      for i in self.__entries :
         if isinstance(i, FullFrame) :
            return i.get_local_variables()

      return []

   def get_raw(self) :
      return self.number_of_entries.get_value_buff() + \
             ''.join(x.get_raw() for x in self.__entries )

   def show(self) :
      bytecode._Print("NUMBER_OF_ENTRIES", self.number_of_entries.get_value())
      for i in self.__entries :
         i.show()

   def _fix_attributes(self, new_cm) :
      for i in self.__entries :
         i._fix_attributes( new_cm )

   def set_cm(self, cm) :
      self.__CM = cm
      for i in self.__entries :
         i.set_cm( cm )

class InnerClassesDesc :
   def __init__(self, class_manager, buff) :
      INNER_CLASSES_FORMAT = [ ">BBBB", "inner_class_info_index outer_class_info_index inner_name_index inner_class_access_flags" ]
      
      self.__CM = class_manager

      self.__raw_buff = buff.read( calcsize( INNER_CLASSES_FORMAT[0] ) )

      self.format = SVs( INNER_CLASSES_FORMAT[0], namedtuple( "InnerClassesFormat", INNER_CLASSES_FORMAT[1] ), self.__raw_buff )

   def show(self) :
      print self.format

   def get_raw(self) :
      return self.format.get_value_buff()

   def set_cm(self, cm) :
      self.__CM = cm

class InnerClassesAttribute(BasicAttribute) :
   def __init__(self, class_manager, buff) :
      self.__CM = class_manager

      super(InnerClassesAttribute, self).__init__()
      # u2 attribute_name_index;
      # u4 attribute_length
      
      # u2 number_of_classes;
      self.number_of_classes = SV( '>H', buff.read(2) )

      # {  u2 inner_class_info_index;          
      #    u2 outer_class_info_index;            
      #    u2 inner_name_index;          
      #    u2 inner_class_access_flags;          
      # } classes[number_of_classes];
      self.__classes = []

      for i in range(0, self.number_of_classes.get_value()) :
         self.__classes.append( InnerClassesDesc( self.__CM, buff ) )

   def get_classes(self) :
      return self.__classes

   def show(self) :
      print self.number_of_classes
      for i in self.__classes :
         i.show()

   def set_cm(self, cm) :
      self.__CM = cm
      for i in self.__classes :
         i.set_cm( cm )

   def get_raw(self) :
      return self.number_of_classes.get_value_buff + \
             ''.join(x.get_raw() for x in self.__classes)

class ConstantValueAttribute(BasicAttribute) :
   def __init__(self, class_manager, buff) :
      self.__CM = class_manager

      super(ConstantValueAttribute, self).__init__()
      # u2 attribute_name_index;
      # u4 attribute_length;

      # u2 constantvalue_index;
      self.constantvalue_index = SV( '>H', buff.read(2) )

   def show(self) :
      print self.constantvalue_index

   def set_cm(self, cm) :
      self.__CM = cm

   def get_raw(self) :
      return self.constantvalue_index

      
class AttributeInfo :
   """AttributeInfo manages each attribute info (Code, SourceFile ....)"""
   def __init__(self, class_manager, buff) :
      self.__CM = class_manager
      self.__raw_buff = buff.read( calcsize( ATTRIBUTE_INFO[0] ) ) 
      
      self.format = SVs( ATTRIBUTE_INFO[0], ATTRIBUTE_INFO[1], self.__raw_buff )
      self.__name = self.__CM.get_string( self.format.get_value().attribute_name_index )

      if self.__name == "Code" :
         self.__info = CodeAttribute( self.__CM, buff ) 
      elif self.__name == "SourceFile" :
         self.__info = SourceFileAttribute( buff )
      elif self.__name == "Exceptions" :
         self.__info = ExceptionsAttribute( buff )
      elif self.__name == "LineNumberTable" :
         self.__info = LineNumberTableAttribute( buff )
      elif self.__name == "LocalVariableTable" :
         self.__info = LocalVariableTableAttribute( buff )
      elif self.__name == "StackMapTable" :
         self.__info = StackMapTableAttribute( self.__CM, buff )
      elif self.__name == "InnerClasses" :
         self.__info = InnerClassesAttribute( self.__CM, buff )
      elif self.__name == "ConstantValue" :
         self.__info = ConstantValueAttribute( self.__CM, buff )
      else :
         bytecode.Exit( "AttributeInfo %s doesn't exit" % self.__name )

   def get_item(self) :
      """Return the specific attribute info"""
      return self.__info

   def get_name(self) :
      """Return the name of the attribute"""
      return self.__name

   def get_raw(self) :
      v1 = self.format.get_value().attribute_length
      v2 = len(self.__info.get_raw())
      if v1 != v2 :
         self.set_attribute_length( v2 )

      return self.format.get_value_buff() + self.__info.get_raw()

   def get_attribute_name_index(self) :
      return self.format.get_value().attribute_name_index

   def set_attribute_name_index(self, value) :
      self.format.set_value( { "attribute_name_index" : value } )

   def set_attribute_length(self, value) :
      self.format.set_value( { "attribute_length" : value } )

   def get_attributes(self) :
      return self.format

   def _fix_attributes(self, new_cm) :
      self.__info._fix_attributes( new_cm )

   def set_cm(self, cm) :
      self.__CM = cm
      self.__info.set_cm( cm )

   def show(self) :
      print self.format, self.__name
      if self.__info != None :
         self.__info.show()

class ClassManager :
   """ClassManager can be used by all classes to get more information"""
   def __init__(self, constant_pool, constant_pool_count) :
      self.__constant_pool = constant_pool
      self.__constant_pool_count = constant_pool_count

      self.__this_class = None

   def get_value(self, idx) :
      name = self.get_item(idx[0]).get_name()
      if name == "CONSTANT_Integer" :
         return [ name, self.get_item(idx[0]).get_format().get_value().bytes ]
      elif name == "CONSTANT_String" :
         return [ name, self.get_string( self.get_item(idx[0]).get_format().get_value().string_index ) ]

      bytecode.Exit( "get_value not yet implemented for %s" % name )

   def get_item(self, idx) :
      return self.__constant_pool[ idx - 1]

   def get_method(self, idx) :
      if self.get_item(idx).get_name() != "CONSTANT_Methodref" :
         return []

      class_idx = self.get_item(idx).get_class_index()
      name_and_type_idx = self.get_item(idx).get_name_and_type_index()

      return [ self.get_string( self.get_item(class_idx).get_name_index() ), 
               self.get_string( self.get_item(name_and_type_idx).get_name_index() ),
               self.get_string( self.get_item(name_and_type_idx).get_descriptor_index() )
             ]

   def get_method_index(self, class_name, name, descriptor) :
      idx = 1 
      for i in self.__constant_pool :
         res = self.get_method( idx ) 
         if res != [] :
            m_class_name, m_name, m_descriptor = res
            if m_class_name == class_name and m_name == name and m_descriptor == descriptor :
               return idx
         idx += 1

      return -1

   def get_field(self, idx) :
      if self.get_item(idx).get_name() != "CONSTANT_Fieldref" :
         return []

      class_idx = self.get_item(idx).get_class_index()
      name_and_type_idx = self.get_item(idx).get_name_and_type_index()

      return [ self.get_string( self.get_item(class_idx).get_name_index() ),               
               self.get_string( self.get_item(name_and_type_idx).get_name_index() ),               
               self.get_string( self.get_item(name_and_type_idx).get_descriptor_index() )
             ]

   def get_field_index(self, name, descriptor) :
      idx = 1 
      for i in self.__constant_pool :
         res = self.get_field( idx ) 
         if res != [] :
            _, m_name, m_descriptor = res
            if m_name == name and m_descriptor == descriptor :
               return idx
         idx += 1

   def get_class(self, idx):
      return [ self.get_string( self.get_item(idx).get_name_index() ) ]

   def get_array_type(self, idx) :
      return ARRAY_TYPE[ idx[0] ]

   def get_string_index(self, name) :
      idx = 1 
      for i in self.__constant_pool :
         if i.get_name() == "CONSTANT_Utf8" :
            if i.get_bytes() == name :
               return idx 
         idx += 1
      return -1

   def get_integer_index(self, value) :
      idx = 1
      for i in self.__constant_pool :
         if i.get_name() == "CONSTANT_Integer" :
            if i.get_format().get_value().bytes == value :
               return idx
         idx += 1
      return -1

   def get_cstring_index(self, value) :
      idx = 1
      for i in self.__constant_pool :
         if i.get_name() == "CONSTANT_String" :
            if self.get_string( i.get_format().get_value().string_index ) == value :
               return idx
         idx += 1
      return -1

   def get_name_and_type_index(self, name_method_index, descriptor_method_index) :
      idx = 1
      for i in self.__constant_pool :
         if i.get_name() == "CONSTANT_NameAndType" :
            value = i.get_format().get_value()
            if value.name_index == name_method_index and value.descriptor_index == descriptor_method_index :
               return idx
         idx += 1
      return -1

   def get_class_by_index(self, name_index) :
      idx = 1
      for i in self.__constant_pool :
         if i.get_name() == "CONSTANT_Class" :
            value = i.get_format().get_value()
            if value.name_index == name_index :
               return idx
         idx += 1
      return -1 

   def get_method_ref_index(self, new_class_index, new_name_and_type_index) :
      idx = 1
      for i in self.__constant_pool :
         if i.get_name() == "CONSTANT_Methodref" :
            value = i.get_format().get_value()
            if value.class_index == new_class_index and value.name_and_type_index == new_name_and_type_index :
               return idx
         idx += 1
      return -1 

   def get_field_ref_index(self, new_class_index, new_name_and_type_index) :
      idx = 1
      for i in self.__constant_pool :
         if i.get_name() == "CONSTANT_Fieldref" :
            value = i.get_format().get_value()
            if value.class_index == new_class_index and value.name_and_type_index == new_name_and_type_index :
               return idx
         idx += 1
      return -1

   def get_class_index(self, method_name) :
      idx = 1 
      for i in self.__constant_pool :
         res = self.get_method( idx )
         if res != [] :
            _, name, _ = res
            if name == method_name :
               return i.get_class_index()
         idx += 1
      return -1

   def get_string(self, idx) :
      if self.__constant_pool[idx - 1].get_name() == "CONSTANT_Utf8" :
         return self.__constant_pool[idx - 1].get_bytes()
      return None

   def set_string(self, idx, name) :
      if self.__constant_pool[idx - 1].get_name() == "CONSTANT_Utf8" :
         self.__constant_pool[idx - 1].set_bytes( name )
      else :
         bytecode.Exit( "invalid index %d to set string %s" % (idx, name) )

   def add_string(self, name) :
      name_index = self.get_string_index(name)
      if name_index != -1 :
         return name_index

      tag_value = INVERT_CONSTANT_INFO[ "CONSTANT_Utf8" ]
      buff = pack( CONSTANT_INFO[ tag_value ][1], tag_value, len(name) ) + pack( ">%ss" % len(name), name )
      ci = CONSTANT_INFO[ tag_value ][-1]( self, bytecode.BuffHandle( buff ) )
      
      self.__constant_pool.append( ci )
      self.__constant_pool_count.set_value( self.__constant_pool_count.get_value() + 1 )
   
      return self.__constant_pool_count.get_value() - 1

   def set_this_class(self, this_class) :
      self.__this_class = this_class

   def get_this_class(self) :
      return self.__this_class.get_value()

   def get_this_class_name(self) :
      return self.get_class( self.__this_class.get_value() )[0]

   def add_constant_pool(self, elem) :
      self.__constant_pool.append( elem )
      self.__constant_pool_count.set_value( self.__constant_pool_count.get_value() + 1 )
      
   def get_constant_pool_count(self) :
      return self.__constant_pool_count.get_value()

   def create_class(self, name) :
      class_name_index = self.add_string( name )
      return self._create_class( class_name_index )
   
   def _create_class(self, class_name_index) :
      class_index = self.get_class_by_index( class_name_index )
      if class_index == -1 :
         new_class = CreateClass( self, class_name_index )
         self.add_constant_pool( Class( self, bytecode.BuffHandle( new_class.get_raw() ) ) )
         class_index = self.get_constant_pool_count() - 1
      return class_index

   def create_name_and_type(self, name, desc) :
      name_method_index = self.add_string( name )
      descriptor_method_index = self.add_string( desc )

      return self._create_name_and_type( name_method_index, descriptor_method_index )

   def create_name_and_type_by_index(self, name_method_index, descriptor_method_index) :
      return self._create_name_and_type( name_method_index, descriptor_method_index )

   def _create_name_and_type(self, name_method_index, descriptor_method_index) :
      name_and_type_index = self.get_name_and_type_index( name_method_index, descriptor_method_index )
      if name_and_type_index == -1 :
         new_nat = CreateNameAndType( self, name_method_index, descriptor_method_index )
         self.add_constant_pool( NameAndType( self, bytecode.BuffHandle( new_nat.get_raw() ) ) )
         name_and_type_index = self.get_constant_pool_count() - 1
      return name_and_type_index

   def create_method_ref(self, new_class_index, new_name_and_type_index) :
      new_mr_index = self.get_method_ref_index( new_class_index, new_name_and_type_index )
      if new_mr_index == -1 :
         new_mr = CreateMethodRef( self, new_class_index, new_name_and_type_index )
         self.add_constant_pool( MethodRef( self, bytecode.BuffHandle( new_mr.get_raw() ) ) )
         new_mr_index = self.get_constant_pool_count() - 1
      return new_mr_index

   def create_field_ref(self, new_class_index, new_name_and_type_index) :
      new_fr_index = self.get_field_ref_index( new_class_index, new_name_and_type_index )
      if new_fr_index == -1 :
         new_fr = CreateFieldRef( self, new_class_index, new_name_and_type_index )
         self.add_constant_pool( FieldRef( self, bytecode.BuffHandle( new_mr.get_raw() ) ) )
         new_fr_index = self.get_constant_pool_count() - 1
      return new_fr_index

   def create_integer(self, value) :
      new_int_index = self.get_integer_index( value )
      if new_int_index == -1 :
         new_int = CreateInteger( value )
         self.add_constant_pool( Integer( self, bytecode.BuffHandle( new_int.get_raw() ) ) )
         new_int_index = self.get_constant_pool_count() - 1

      return new_int_index

   def create_string(self, value) :
      new_string_index = self.get_cstring_index( value )
      if new_string_index == -1 :
         new_string = CreateString( self, value )
         self.add_constant_pool( String( self, bytecode.BuffHandle( new_string.get_raw() ) ) )
         new_string_index = self.get_constant_pool_count() - 1
      return new_string_index


class JVMFormat(bytecode._Bytecode) :
   """An object which is the main class to handle properly a class file.
      Exported fields : magic, minor_version, major_version, constant_pool_count, access_flags, this_class, super_class, interfaces_count, fields_count, methods_count, attributes_count

      @param buff : the buffer which represents the open file
   """
   def __init__(self, buff) :
      super(JVMFormat, self).__init__( buff )
      super(JVMFormat, self).register( bytecode.SHOW, self.show )

      self._load_class()

   def _load_class(self) :
      # u4 magic;
      # u2 minor_version;
      # u2 major_version;
      self.magic = SV( '>L', self.read( 4 ) ) 
      self.minor_version = SV( '>H', self.read( 2 ) ) 
      self.major_version = SV( '>H', self.read( 2 ) )
    
      # u2 constant_pool_count;
      self.constant_pool_count = SV( '>H', self.read( 2 ) )

      #  cp_info constant_pool[constant_pool_count-1];
      self.__constant_pool = []
      self.__CM = ClassManager( self.__constant_pool, self.constant_pool_count )
      for i in range(1, self.constant_pool_count.get_value()) :
         tag = SV( '>B', self.read_b( 1 ) )

         if tag.get_value() not in CONSTANT_INFO : 
            bytecode.Exit( "tag not in CONSTANT_INFO" )

         ci = CONSTANT_INFO[ tag.get_value() ][-1]( self.__CM, self )
         
         self.__constant_pool.append( ci )


      # u2 access_flags;
      # u2 this_class;
      # u2 super_class;
      self.access_flags       = SV( '>H', self.read( 2 ) )
      self.this_class         = SV( '>H', self.read( 2 ) )
      self.super_class        = SV( '>H', self.read( 2 ) )


      self.__CM.set_this_class( self.this_class )

      # u2 interfaces_count;
      self.interfaces_count   = SV( '>H', self.read( 2 ) )

      #FIXME
      # u2 interfaces[interfaces_count];
      self.__interfaces = []
      for i in range(0, self.interfaces_count.get_value()) :
         tag = SV( '>H', self.read( 2 ) )
         self.__interfaces.append( tag )


      # u2 fields_count;
      self.fields_count = SV( '>H', self.read( 2 ) )

      # field_info fields[fields_count];
      self.__fields = []
      for i in range(0, self.fields_count.get_value()) :
         fi = FieldInfo( self.__CM, self ) 

         self.__fields.append( fi )

      # u2 methods_count;
      self.methods_count = SV( '>H', self.read( 2 ) )

      # method_info methods[methods_count];
      self.__methods = []
      for i in range(0, self.methods_count.get_value()) :
         mi = MethodInfo( self.__CM, self ) 
         
         self.__methods.append( mi )
         
      # u2 attributes_count;
      self.attributes_count = SV( '>H', self.read( 2 ) )

      # attribute_info attributes[attributes_count];
      self.__attributes = []
      for i in range(0, self.attributes_count.get_value()) :
         ai = AttributeInfo( self.__CM, self ) 
         self.__attributes.append( ai )
      
   def get_field(self, name) :
      """Return into a list all fields which corresponds to the regexp 
         
         @param name : the name of the field (a regexp)
      """
      prog = re.compile( name )
      fields = []
      for i in self.__fields :
         if prog.match( i.get_name() ) :
            fields.append( i )
      return fields

   def get_method_descriptor(self, class_name, method_name, descriptor) :
      # FIXME : handle multiple class name ?
      if class_name != None :
         if class_name != self.__CM.get_this_class_name() :
            return None

      prog_method_name = re.compile( method_name )
      for i in self.__methods :
         if prog_method_name.match( i.get_name() ) and descriptor == i.get_descriptor() :
            return i
      return None

   def get_method(self, name) :
      """Return into a list all methods which corresponds to the regexp

         @param name : the name of the method (a regexp)
      """
      prog = re.compile( name )
      methods = []
      for i in self.__methods :
         if prog.match( i.get_name() ) :
            methods.append( i )
      return methods 

   def get_fields(self) :
      """Return all objects fields"""
      return self.__fields

   def get_methods(self) :
      """Return all objects methods"""
      return self.__methods

   def get_constant_pool(self) :
      """Return the constant pool list"""
      return self.__constant_pool

   def get_strings(self) :
      """Return all strings into the class"""
      l = []
      for i in self.__constant_pool :
         if i.get_name() == "CONSTANT_Utf8" :
            l.append( i.get_bytes() )
      return l 

   def get_class_manager(self) :
      """Return directly the class manager"""
      return self.__CM

   def show(self) :
      """Show the .class format into a human readable format"""
      bytecode._Print( "MAGIC", self.magic.get_value() )
      bytecode._Print( "MINOR VERSION", self.minor_version.get_value() )
      bytecode._Print( "MAJOR VERSION", self.major_version.get_value() )
      bytecode._Print( "CONSTANT POOL COUNT", self.constant_pool_count.get_value() )
      
      nb = 0
      for i in self.__constant_pool :
         print nb,
         i.show()
         nb += 1


      bytecode._Print( "ACCESS FLAGS", self.access_flags.get_value() )
      bytecode._Print( "THIS CLASS", self.this_class.get_value() )
      bytecode._Print( "SUPER CLASS", self.super_class.get_value() )

      bytecode._Print( "INTERFACE COUNT", self.interfaces_count.get_value() )
      nb = 0
      for i in self.__interfaces :
         print nb,
         i.show()
      
      bytecode._Print( "FIELDS COUNT", self.fields_count.get_value() )
      nb = 0
      for i in self.__fields :
         print nb,
         i.show()
         nb += 1


      bytecode._Print( "METHODS COUNT", self.methods_count.get_value() )
      nb = 0
      for i in self.__methods :
         print nb,
         i.show()
         nb += 1

      
      bytecode._Print( "ATTRIBUTES COUNT", self.attributes_count.get_value() )
      nb = 0
      for i in self.__attributes :
         print nb,
         i.show()
         nb += 1
   
   def insert_string(self, value) :
      """Insert a string into the constant pool list (Constant_Utf8)
   
         @param value : the new string
      """
      self.__CM.add_string( value )

   def insert_craft_method(self, name, proto, codes) :
      """Insert a craft method into the class
  
         @param name : the name of the new method
         @param proto : a list which describe the method ( [ ACCESS_FLAGS, RETURN_TYPE, ARGUMENTS ], ie : [ "ACC_PUBLIC", "[B", "[B" ] )
         @param codes : a list which represents the code into a human readable format ( [ "aconst_null" ], [ "areturn" ] ] ) 
      """
      # Create new method
      new_method = CreateMethodInfo(self.__CM, name, proto, codes)

      # Insert the method by casting it directly into a MethodInfo with the raw buffer
      self._insert_basic_method( MethodInfo( self.__CM, bytecode.BuffHandle( new_method.get_raw() ) ) )

   def insert_direct_method(self, name, ref_method) :
      """Insert a direct method (MethodInfo Object) into the class
   
         @param name : the name of the new method
         @param ref_method : the MethodInfo Object 
      """
      if ref_method == None :
         return

      # Change the name_index
      name_index = self.__CM.get_string_index( name )
      if name_index != -1 :
         bytecode.Exit( "method %s already exits" % name )

      name_index = self.__CM.add_string( name )
      ref_method.set_name_index( name_index )
      
      # Change the descriptor_index
      descriptor_index = self.__CM.get_string_index( ref_method.get_descriptor() )
      if descriptor_index == -1 :
         descriptor_index = self.__CM.add_string( ref_method.get_descriptor() )
      ref_method.set_descriptor_index( descriptor_index ) 

      # Change attributes name index
      self._fix_attributes_external( ref_method )

      # Change internal index
      self._fix_attributes_internal( ref_method )

      # Insert the method
      self._insert_basic_method( ref_method )
     
   def _fix_attributes_external(self, ref_method) :
      for i in ref_method.get_attributes() :
         attribute_name_index = self.__CM.add_string( i.get_name() )
         
         i.set_attribute_name_index( attribute_name_index )
         
         self._fix_attributes_external( i.get_item() )

   def _fix_attributes_internal(self, ref_method) :
      for i in ref_method.get_attributes() :
         attribute_name_index = self.__CM.add_string( i.get_name() )

         i._fix_attributes( self.__CM )

         i.set_attribute_name_index( attribute_name_index )
         
   def _insert_basic_method(self, ref_method) :
      # Add a MethodRef and a NameAndType
      name_and_type_index = self.__CM.create_name_and_type_by_index( ref_method.get_name_index(), ref_method.get_descriptor_index() )

      self.__CM.create_method_ref( self.__CM.get_this_class(), name_and_type_index )

      # Change the class manager
      ref_method.set_cm( self.__CM )
      
      # Insert libraries/constants dependances 
      methods = ref_method._patch_bytecodes()

      # FIXME : insert needed fields + methods
      prog = re.compile( "^java*" )
      for i in methods :
         if prog.match( i[0] ) == None :
            bytecode.Exit( "ooooops" )

      
      #ref_method.show()

      # Insert the method
      self.__methods.append( ref_method )
      self.methods_count.set_value( self.methods_count.get_value() + 1 )

   def _get_raw(self) :
      # u4 magic;      
      # u2 minor_version;      
      # u2 major_version;
      buff = self.magic.get_value_buff()
      buff += self.minor_version.get_value_buff()
      buff += self.major_version.get_value_buff()
      
      # u2 constant_pool_count;
      buff += self.constant_pool_count.get_value_buff()

      #  cp_info constant_pool[constant_pool_count-1];
      for i in self.__constant_pool :
         buff += i.get_raw()

      # u2 access_flags;
      # u2 this_class;
      # u2 super_class;
      buff += self.access_flags.get_value_buff()
      buff += self.this_class.get_value_buff()
      buff += self.super_class.get_value_buff()

      # u2 interfaces_count;               
      buff += self.interfaces_count.get_value_buff()

      # u2 interfaces[interfaces_count];
      for i in self.__interfaces :
         buff += i.get_value_buff()

      # u2 fields_count;
      buff += self.fields_count.get_value_buff()

      # field_info fields[fields_count];
      for i in self.__fields :
         buff += i.get_raw()

      # u2 methods_count;
      buff += self.methods_count.get_value_buff()

      # method_info methods[methods_count];
      for i in self.__methods :
         buff += i.get_raw()

      # u2 attributes_count;
      buff += self.attributes_count.get_value_buff()
      
      # attribute_info attributes[attributes_count];
      for i in self.__attributes :
         buff += i.get_raw()

      return buff

   def save(self) :
      """Return the class (with the modifications) into raw format
      
         @rtype: string
      """
      return self._get_raw()

   def get_INTEGER_INSTRUCTIONS(self) :
      return INTEGER_INSTRUCTIONS

