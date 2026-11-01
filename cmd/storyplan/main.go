// storyplan converts timestamped narration transcripts into an editable scene manifest.
package main

import (
 "encoding/json"
 "flag"
 "fmt"
 "io"
 "os"
 "syncshotgo/internal/storyplan"
)

func run(args []string) error {
 f:=flag.NewFlagSet("storyplan",flag.ContinueOnError)
 input:=f.String("transcript","","JSON transcript containing audio, duration_seconds and timestamped segments")
 output:=f.String("output","","destination JSON scene plan (must not exist)")
 style:=f.String("style",storyplan.DefaultStyle,"mythological_3d, cartoon_2d, or cinematic_realistic")
 seconds:=f.Float64("scene-seconds",8,"maximum scene duration")
 if err:=f.Parse(args);err!=nil{return err}
 if f.NArg()!=0||*input==""||*output=="" {return fmt.Errorf("usage: storyplan --transcript transcript.json --output scenes.json [--style mythological_3d]")}
 file,err:=os.Open(*input);if err!=nil{return err};defer file.Close()
 dec:=json.NewDecoder(io.LimitReader(file,16*1024*1024));dec.DisallowUnknownFields()
 var src storyplan.Input
 if err:=dec.Decode(&src);err!=nil{return fmt.Errorf("decode transcript: %w",err)}
 var extra any
 if err:=dec.Decode(&extra);err!=io.EOF{return fmt.Errorf("transcript must be a single JSON object")}
 plan,err:=storyplan.Build(src,*style,*seconds);if err!=nil{return err}
 dest,err:=os.OpenFile(*output,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if err!=nil{return err}
 defer dest.Close()
 enc:=json.NewEncoder(dest);enc.SetIndent("","  ")
 if err:=enc.Encode(plan);err!=nil{dest.Close();os.Remove(*output);return err}
 fmt.Printf("Wrote %d scenes to %s\n",len(plan.Scenes),*output)
 return nil
}
func main(){if err:=run(os.Args[1:]);err!=nil{fmt.Fprintln(os.Stderr,"storyplan:",err);os.Exit(1)}}
