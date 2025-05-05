import os
import re

def main():
  # .env ファイルは、read_env.py の一つ上の階層にある前提
  env_file = os.path.join(os.path.dirname(__file__), "../.env")
  tfvars_file = os.path.join(os.path.dirname(__file__), "./stg.tfvars")
  
  with open(tfvars_file, "r") as f:
      string = f.read()
      string = re.sub(r"#.*?\n", "\n", string) # コメント除去
      target = re.findall(r"\nsecrets\s*\=\s*\{([^\}]+?)\}", string)[0]
      print(target)
  
  envs = []
  for line in target.split("\n"):
    if "=" in line:
      key, value = line.strip().split("=")
      envs.append(f'{key.upper()}={value}') 
    
  with open(env_file, "w") as f:
    f.write("\n".join(envs))


if __name__ == "__main__":
    main()