#!/bin/bash
gcc -o task1 task1.c

if [ $? -eq 0 ]; then

	for i in {1..5}
	do
		nice -n 0 taskset -c 11 ./task1 &
	done


	for i in {6..10}
	do	
		nice -n 4 taskset -c 11 ./task1 &
	done
fi
