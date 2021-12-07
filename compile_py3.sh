#!/usr/bin/env bash
# Get script directory.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo $DIR

if swig_loc="$(type -p "swig")" || [[ -z $swig_loc ]];
then
    swig -c++ -python $DIR/src/NIRScanner.i
else
    echo "Did not detect swig, using generated Python Interface."
fi

# Find Python version & set library path.
PYTHON3_VERSION=$(/usr/bin/python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')

# Compile.
gcc -fpic -c $DIR/src/*.c
g++ -fpic -c $DIR/src/*.cpp
g++ -fpic -c $DIR/src/*.cxx -I/usr/include/python${PYTHON3_VERSION}
mv ./*.o $DIR/src/build
g++ -shared $DIR/src/build/*.o -ludev -lpython${PYTHON3_VERSION} -o $DIR/src/build/_NIRScanner.so.3
cp $DIR/src/build/_NIRScanner.so.3 $DIR/lib/
cp $DIR/lib/_NIRScanner.so.3 $DIR/_NIRScanner.so

# Clean .o files.
rm $DIR/src/build/*.o