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

    my $cmd = "rg -uu -N '$target' '$corpus' | rg -m 1 '$anchor'";
    my $result = `$cmd`;
    
    if ($result) {
        # 1. Remove the trailing newline
        chomp($result);
        
        # 2. Strip bracketed ID tags and trailing spaces at the start of the line
        $result =~ s/^\[.*?\]\s*//;
        
        # 3. Output as strict TSV: Target \t Clean_Sentence
        print "$target\t$result\n";
    }
}
