package main

import (
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func TestCommand(t *testing.T) {
 dir:=t.TempDir()
 src:=filepath.Join(dir,"transcript.json")
 out:=filepath.Join(dir,"scenes.json")
 err:=os.WriteFile(src,[]byte(`{"audio":"example.m4a","duration_seconds":10,"segments":[{"start":0,"end":10,"text":"hello"}]}`),0600)
 if err!=nil{t.Fatal(err)}
 if err:=run([]string{"--transcript",src,"--output",out,"--scene-seconds","5"});err!=nil{t.Fatal(err)}
 contents,err:=os.ReadFile(out);if err!=nil{t.Fatal(err)}
 if !strings.Contains(string(contents),`"index": 2`){t.Fatal("missing second scene")}
 if err:=run([]string{"--transcript",src,"--output",out});err==nil{t.Fatal("must not overwrite existing plan")}
}
