package utils

import (
 "strings"
 "testing"
)

func TestFormatProgressBar(t *testing.T) {
 cases:=[]struct{pct int; want string}{
  {-10,"["+strings.Repeat("-",30)+"]   0%"},
  {0,"["+strings.Repeat("-",30)+"]   0%"},
  {50,"["+strings.Repeat("=",15)+strings.Repeat("-",15)+"]  50%"},
  {100,"["+strings.Repeat("=",30)+"] 100%"},
  {120,"["+strings.Repeat("=",30)+"] 100%"},
 }
 for _,tc:=range cases {
  if got:=FormatProgressBar(tc.pct);got!=tc.want {t.Errorf("pct=%d got %q want %q",tc.pct,got,tc.want)}
 }
}
