#!/usr/bin/perl
use strict;
use warnings;

my $corpus = shift @ARGV;
die "Usage: perl miner_pipe.pl /path/to/corpus\n" unless defined $corpus;

while (my $line = <STDIN>) {
    $line =~ s/[\r\n]+$//;
    next if $line =~ /^\s*$/;

    my ($target, $anchor) = split(/\s+/, $line);
    next unless $target && $anchor;

    my $cmd = "rg --no-filename -uu -N '$target' '$corpus' | rg -m 1 '$anchor'";
    my $result = `$cmd`;
    
    if ($result) {
        chomp($result);
        
        # 1. Strip the bracketed ID tags (e.g. [146782006]) and leading spaces
        $result =~ s/^\[.*?\]\s*//;
        
        # 2. Strip all Unity/HTML formatting tags (e.g. <color=#dbc291ff> or </color>)
        $result =~ s/<[^>]+>//g;
        
        # Output as strict TSV: Target \t Clean_Sentence
        print "$target\t$result\n";
    }
}
