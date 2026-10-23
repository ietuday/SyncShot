package subtitles

import (
 "bytes"
 "context"
 "fmt"
 "os"
 "os/exec"
 "path/filepath"
 "regexp"
 "strconv"
 "strings"
)

var timing=regexp.MustCompile(`^(\d{2,}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2,}):(\d{2}):(\d{2}),(\d{3})(?: .*)?$`)

// ValidateSRT checks timestamp ordering, numbering and nonempty caption text.
func ValidateSRT(data []byte) error {
 data=bytes.TrimSpace(bytes.TrimPrefix(data,[]byte{0xef,0xbb,0xbf}))
 if len(data)==0 {return fmt.Errorf("empty SRT")}
 normalized:=strings.ReplaceAll(strings.ReplaceAll(string(data),"\r\n","\n"),"\r","\n")
 blocks:=strings.Split(normalized,"\n\n")
 previous:=int64(0)
 for i,block:=range blocks {
  lines:=strings.Split(strings.TrimSpace(block),"\n")
  if len(lines)<3 {return fmt.Errorf("caption %d requires number, timing and text",i+1)}
  number,err:=strconv.Atoi(strings.TrimSpace(lines[0]))
  if err!=nil || number!=i+1 {return fmt.Errorf("caption %d invalid sequence",i+1)}
  m:=timing.FindStringSubmatch(strings.TrimSpace(lines[1]))
  if m==nil {return fmt.Errorf("caption %d invalid timestamps",i+1)}
  parse:=func(offset int)(int64,error){
   n:=make([]int64,4)
   for j:=0;j<4;j++ {v,e:=strconv.ParseInt(m[offset+j],10,64);if e!=nil{return 0,e};n[j]=v}
   if n[1]>=60 || n[2]>=60 || n[3]>=1000 {return 0,fmt.Errorf("invalid time parts")}
   return ((n[0]*3600+n[1]*60+n[2])*1000+n[3]),nil
  }
  start,e1:=parse(1);end,e2:=parse(5)
  if e1!=nil || e2!=nil || start<previous || end<=start {return fmt.Errorf("caption %d invalid or overlapping time range",i+1)}
  previous=end
  if strings.TrimSpace(strings.Join(lines[2:],""))=="" {return fmt.Errorf("caption %d has no text",i+1)}
 }
 return nil
}

// Prepare copies an authored SRT or invokes a locally installed Whisper CLI
// to transcribe audio, then validates the resulting captions.
func Prepare(ctx context.Context, audio, source, mode, workDir string) (string,error) {
 if mode=="" && source=="" {return "",nil}
 if mode=="" {mode="import"}
 if err:=os.MkdirAll(workDir,0755);err!=nil{return "",err}
 target:=filepath.Join(workDir,"captions.srt")
 switch mode {
 case "import":
  if source=="" {return "",fmt.Errorf("subtitle import requires an SRT file")}
  b,err:=os.ReadFile(source);if err!=nil{return "",fmt.Errorf("read SRT: %w",err)}
  if err:=ValidateSRT(b);err!=nil{return "",err}
  if err:=os.WriteFile(target,b,0644);err!=nil{return "",err}
 case "whisper":
  if source!="" {return "",fmt.Errorf("subtitle source cannot be combined with whisper mode")}
  // Whisper writes <audio basename>.srt; no shell is involved.
  command:=exec.CommandContext(ctx,"whisper",audio,"--model","base","--output_format","srt","--output_dir",workDir)
  out,err:=command.CombinedOutput()
  if err!=nil{return "",fmt.Errorf("whisper transcription failed (install openai-whisper CLI): %w: %s",err,string(out))}
  produced:=filepath.Join(workDir,strings.TrimSuffix(filepath.Base(audio),filepath.Ext(audio))+".srt")
  b,err:=os.ReadFile(produced);if err!=nil{return "",err}
  if err:=ValidateSRT(b);err!=nil{return "",fmt.Errorf("whisper SRT: %w",err)}
  if err:=os.WriteFile(target,b,0644);err!=nil{return "",err}
 default:return "",fmt.Errorf("unsupported subtitle mode %q",mode)
 }
 return target,nil
}
