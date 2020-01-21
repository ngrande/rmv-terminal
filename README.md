# rmv-terminal

## Documentation
Official Documentation from RMV: https://opendata.rmv.de/site/start.html
+ API overview: https://www.rmv.de/hapi/
+ XML description:  https://www.rmv.de/hapi/xsd

## Example

    rmv-terminal[ master]$ ./rmv-terminal.py Galluswarte --lines "S6" --direction "Messe"
    S6 -> Friedberg (Hessen) Bahnhof: 8m
    S6 -> Friedberg (Hessen) Bahnhof: 23m
    S6 -> Karben-Groß-Karben Bahnhof: 38m
    S6 -> Friedberg (Hessen) Bahnhof: 53m

## Help

simply append ```--help``` and you get a list of options:

    rmv-terminal[ master]$ ./rmv-terminal.py Galluswarte --help
    usage: rmv-terminal.py [-h] [--direction DIRECTION] [--lines LINES] [-n N] [--debug] [--i3] station
    
    positional arguments:
      station               request information for a train station
    
    optional arguments:
      -h, --help            show this help message and exit
      --direction DIRECTION
                            direction of the trains
      --lines LINES         list of lines (separated by comma and negated by !)
      -n N                  number of trains to display
      --debug               enable debug logging
      --i3                  i3 mode
