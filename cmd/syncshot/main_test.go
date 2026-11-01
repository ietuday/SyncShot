package main

import (
 "os"
 "path/filepath"
 "strings"
 "testing"
)

func TestDefaultConfig(t *testing.T){
 c:=defaultConfig()
 if c.FPS!=24||c.ClipSeconds!=50||!c.CinematicEnabled||c.CinematicChunkScenes!=2||c.MaxWorkers!=2 {t.Fatalf("defaults changed: %+v",c)}
}
func TestJSONConfigurationAndOverrides(t *testing.T){
 dir:=t.TempDir()
 path:=filepath.Join(dir,"config.json")
 if err:=os.WriteFile(path,[]byte("{\"FPS\":30,\"CinematicChunkScenes\":2,\"MaxWorkers\":3}"),0600);err!=nil{t.Fatal(err)}
 cfg,err:=loadConfig(path);if err!=nil{t.Fatal(err)}
 if cfg.FPS!=30||cfg.CinematicChunkScenes!=2||cfg.MaxWorkers!=3||cfg.AudioDir!="./inputs/audio"{t.Fatalf("unexpected config: %+v",cfg)}
}
func TestChunkingCanBeDisabledByConfig(t *testing.T){
 path:=filepath.Join(t.TempDir(),"config.json")
 if err:=os.WriteFile(path,[]byte("{\\"CinematicChunkScenes\\":0}"),0600);err!=nil{t.Fatal(err)}
 cfg,err:=loadConfig(path);if err!=nil{t.Fatal(err)}
 if cfg.CinematicChunkScenes!=0{t.Fatalf("explicit opt-out ignored: %+v",cfg)}
}
func TestRejectUnknownConfigField(t *testing.T){
 path:=filepath.Join(t.TempDir(),"config.json")
 if err:=os.WriteFile(path,[]byte("{\"UnknownOption\":true}"),0600);err!=nil{t.Fatal(err)}
 if _,err:=loadConfig(path);err==nil{t.Fatal("unknown config key accepted")}
}
func TestRejectTrailingJSON(t *testing.T){
 path:=filepath.Join(t.TempDir(),"config.json")
 if err:=os.WriteFile(path,[]byte("{} {}"),0600);err!=nil{t.Fatal(err)}
 if _,err:=loadConfig(path);err==nil{t.Fatal("two objects accepted")}
}
func TestCLIInputErrors(t *testing.T){
 for _,args:=range [][]string{{"--timeout=-1s"},{"--unknown-flag"},{"unexpected"}} {
  if err:=run(args);err==nil{t.Fatalf("expected error for %v",args)}
 }
}
func TestDryRunMissingDirectories(t *testing.T){
 if err:=run([]string{"--dry-run","--audio-dir",filepath.Join(t.TempDir(),"missing")});err==nil{t.Fatal("missing input directory accepted")}
}
func TestConfigErrorIncludesPath(t *testing.T){
 _,err:=loadConfig(filepath.Join(t.TempDir(),"missing.json"))
 if err==nil||!strings.Contains(err.Error(),"open config"){t.Fatalf("unexpected error: %v",err)}
}
