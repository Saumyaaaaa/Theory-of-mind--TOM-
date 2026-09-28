const text = 'A very common choice people use is the letter $x$ or the letter $n$ to stand in for that missing amount. If you had $6, and added $x$, you get $x + 6$. Also $y = 3x - 1$.';
const pattern = /(\$(?!\s)[^$\n]*?[a-zA-Z][^$\n]*?(?<!\s)\$)/g;
const parts = text.split(pattern);
console.log(parts);
