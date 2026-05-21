#!/usr/bin/perl
use strict;
use warnings;

# Grab the corpus path from the first argument
my $corpus = shift @ARGV;
die "Usage: perl miner.pl /path/to/corpus\n" unless defined $corpus;

# <STDIN> reads line-by-line automatically, immune to the EOF trap
while (my $line = <STDIN>) {
    # Cleanly strip all trailing newlines (\n) and carriage returns (\r)
    $line =~ s/[\r\n]+$//;
    
    # Skip if the line is empty or just whitespace
    next if $line =~ /^\s*$/;

    # Split the line by any amount of whitespace
    my ($target, $anchor) = split(/\s+/, $line);
    
    # Move on if we didn't get at least two words
    next unless $target && $anchor;

    print "🔍 Searching for [$target] + [$anchor]...\n";

    # Execute the ripgrep pipeline. 
    # Wrapping variables in single quotes prevents shell injection issues.
    my $cmd = "rg -uu -N '$target' '$corpus' | rg -m 1 '$anchor'";
    my $result = `$cmd`;
    
    if ($result) {
        print "✅ Match found:\n$result\n";
    } else {
        print "❌ No match found.\n\n";
    }
}