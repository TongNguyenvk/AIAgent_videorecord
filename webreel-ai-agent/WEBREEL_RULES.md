# Webreel Config Rules

## Critical Rules (Bat Buoc Tuan Thu)

### 1. CSS Selector Quote Rules
- LUON dung dau nhay don (') ben trong chuoi CSS Selector
- TUYET DOI KHONG dung dau nhay kep escape (\")

Dung:
```json
{
  "selector": "input[name='email']"
}
```

Sai:
```json
{
  "selector": "input[name=\"email\"]"
}
```

### 2. Focus Before Type
- Truoc BAT KY hanh dong type nao, HAY tu dong chen them:
  1. Hanh dong moveTo vao chinh phan tu do
  2. Hanh dong click vao chinh phan tu do de lay focus

Vi du:
```json
[
  {
    "action": "moveTo",
    "selector": "input[name='email']"
  },
  {
    "action": "click",
    "selector": "input[name='email']"
  },
  {
    "action": "type",
    "selector": "input[name='email']",
    "text": "user@example.com",
    "charDelay": 50
  }
]
```

### 3. Selector Priority
- UU TIEN su dung selector CSS thay vi text
- Webreel khong the nhan ra text selector trong mot so truong hop

Thu tu uu tien:
1. ID: `#elementId`
2. Name attribute: `input[name='email']`
3. Type attribute: `input[type='password']`
4. Class: `.button-primary`
5. Tag: `button`

TRANH dung:
- Text selector: `button:has-text('Submit')`
- Pseudo-selectors phuc tap

### 4. Selector Format
Selector chuan:
```
input[name='email']
input[type='password']
button[type='submit']
a[href='/dashboard']
#username
.btn-primary
```

## Best Practices

### Pause Timing
- Sau navigate: 2000-4000ms
- Sau click: 500-1000ms
- Sau type: 300-500ms
- Truoc type: 500ms (de element ready)

### CharDelay
- Type binh thuong: 50ms
- Type nhanh: 30ms
- Type cham (nhu nguoi that): 80-100ms

### DefaultDelay
- Gia tri mac dinh: 300-500ms
- Cho video muot ma: 500ms
- Cho video nhanh: 300ms
